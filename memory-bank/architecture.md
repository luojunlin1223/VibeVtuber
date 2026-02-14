# System Architecture

**Last Updated:** 2026-02-15 01:03

## Overview

VibeVtuber is a real-time facial motion capture system that drives Live2D character animations using MediaPipe face tracking. The system uses a decoupled Python-Unity architecture connected via UDP for low-latency streaming.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         VIBE VTUBER                              │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐                    ┌──────────────────────────┐
│  PYTHON TRACKER  │                    │     UNITY RECEIVER       │
│   (MediaPipe)    │                    │   (Live2D Controller)    │
├──────────────────┤                    ├──────────────────────────┤
│                  │                    │                          │
│  Webcam          │                    │  UDP Server              │
│     ↓            │                    │     ↓                    │
│  MediaPipe       │    UDP/JSON        │  Thread-safe Queue       │
│  Face Landmarker │  ───────────────>  │     ↓                    │
│     ↓            │  Port 11111        │  JSON Parser             │
│  52 Blendshapes  │  Localhost         │     ↓                    │
│  + Head Rotation │                    │  FaceData Event          │
│     ↓            │                    │     ↓                    │
│  EMA Smoothing   │                    │  Live2DFaceController    │
│     ↓            │                    │     ↓                    │
│  UDP Sender      │                    │  CubismParameter         │
│                  │                    │     ↓                    │
│                  │                    │  Live2D Model Animation  │
└──────────────────┘                    └──────────────────────────┘
```

## Component Architecture

### Python Side

#### 1. FaceTracker (`face_tracker.py`)
**Responsibility:** MediaPipe integration and blendshape extraction

**Key Functions:**
- Initialize MediaPipe Face Landmarker with blendshapes model
- Process webcam frames at 30 FPS
- Extract 52 ARKit-compatible blendshapes (0.0 - 1.0 range)
- Convert transformation matrix to Euler angles (head rotation)
- Apply Exponential Moving Average (EMA) smoothing

**Dependencies:**
- MediaPipe Face Landmarker v2 with blendshapes
- OpenCV for frame capture
- NumPy for matrix operations

**Output Format:**
```python
{
    "blendshapes": {
        "eyeBlinkLeft": 0.0,
        "eyeBlinkRight": 0.1,
        "jawOpen": 0.45,
        # ... 49 more blendshapes
    },
    "head_rotation": {
        "yaw": 15.5,    # degrees
        "pitch": -10.2,
        "roll": 2.1
    }
}
```

#### 2. NetworkSender (`network_sender.py`)
**Responsibility:** UDP communication with Unity

**Key Functions:**
- Create non-blocking UDP socket
- Serialize face data to JSON
- Merge head rotation into blendshapes as headYaw/Pitch/Roll
- Send fire-and-forget UDP packets

**Message Format:**
```json
{
    "timestamp": 1234567890.123,
    "faceDetected": true,
    "blendshapes": {
        "headYaw": 15.5,
        "headPitch": -10.2,
        "headRoll": 2.1,
        "eyeBlinkLeft": 0.0,
        "eyeBlinkRight": 0.1,
        "jawOpen": 0.45,
        ...
    }
}
```

#### 3. Main Loop (`main.py`)
**Responsibility:** Orchestration and configuration

**Flow:**
1. Load `config.json`
2. Initialize MediaPipe and webcam
3. Main loop:
   ```python
   while True:
       frame = capture()
       face_data = process(frame)
       smoothed_data = smooth(face_data)
       send(smoothed_data)
       display_debug(frame, face_data)  # optional
   ```
4. Cleanup on exit

### Unity Side

#### 1. FaceDataReceiver (Core)
**Responsibility:** Thread-safe UDP reception and parsing

**Architecture Pattern:** Producer-Consumer with Thread Safety

```csharp
Background Thread (Producer)     Main Thread (Consumer)
┌─────────────────────┐         ┌─────────────────────┐
│ UDP Receive Loop    │         │ Update() Loop       │
│   ↓                 │         │   ↓                 │
│ Receive Packet      │         │ TryDequeue()        │
│   ↓                 │  Queue  │   ↓                 │
│ Encoding.UTF8       │ ──────> │ ParseJSON()         │
│   ↓                 │         │   ↓                 │
│ Enqueue(json)       │         │ OnDataReceived.Invoke() │
└─────────────────────┘         └─────────────────────┘
```

**Key Features:**
- Non-blocking background thread for UDP I/O
- `ConcurrentQueue<string>` for thread-safe message passing
- Manual JSON parsing (robust blendshapes extraction)
- Connection status monitoring (2-second timeout)
- UnityEvent-based data distribution
- **Odin Inspector UI** with organized parameter groups

**Thread Safety:**
- Only background thread accesses UDP socket
- Only main thread accesses Unity API
- Queue provides lock-free synchronization

#### 2. FaceData (Data Model)
**Responsibility:** Serializable data structure

```csharp
public class FaceData
{
    public float timestamp;
    public bool faceDetected;
    public Dictionary<string, float> blendshapes;  // 55 parameters

    public float GetBlendshape(string name) {
        return blendshapes.TryGetValue(name, out float value) ? value : 0f;
    }
}
```

#### 3. Live2DFaceController
**Responsibility:** MediaPipe → Live2D parameter mapping

**Architecture Pattern:** Configurable Pipeline with Multi-Stage Transformation

```
Source Parameters → Combine → Invert → Range Remap → Multiply/Offset → Clamp → Smooth → Live2D
```

**ParameterMapping Structure:**
```csharp
class ParameterMapping {
    // Source
    List<string> sourceParameters;  // Multi-select
    CombineMode combineMode;        // How to blend

    // Transformations
    bool invert;                    // 1.0 - value
    float multiplier;               // Scale
    float offset;                   // Shift

    // Range Remapping (ADR-001)
    bool useRemapping;
    float inputMin, inputMax;       // MediaPipe range
    float outputMin, outputMax;     // Live2D range
    bool useSmoothstep;             // S-curve interpolation

    // Final Adjustments
    bool useClamp;
    float clampMin, clampMax;
    bool useSmoothing;              // Temporal smoothing

    // Target
    string live2DParameter;
}
```

**Combine Modes:**
- `None`: Use first source only
- `Average`: (a + b + c) / 3
- `Sum`: a + b + c
- `Max`: max(a, b, c)
- `Min`: min(a, b, c)
- `Difference`: a - b (for eyeLookUp - eyeLookDown)

**Processing Pipeline:**
```csharp
void ApplyParameterMapping(ParameterMapping m, FaceData data) {
    // 1. Get source values
    value = CombineValues(m.sourceParameters, m.combineMode);

    // 2. Invert (optional)
    if (m.invert) value = 1.0f - value;

    // 3. Range Remapping (optional, ADR-001)
    if (m.useRemapping) {
        t = InverseLerp(m.inputMin, m.inputMax, value);
        if (m.useSmoothstep) t = SmoothStep(0, 1, t);
        value = Lerp(m.outputMin, m.outputMax, t);
    }

    // 4. Multiply/Offset
    value = value * m.multiplier + m.offset;

    // 5. Clamp (optional)
    if (m.useClamp) value = Clamp(value, m.clampMin, m.clampMax);

    // 6. Temporal Smoothing (optional)
    if (m.useSmoothing) value = Lerp(smoothedValues[key], value, smoothFactor);

    // 7. Set Live2D parameter
    SetParameter(m.live2DParameter, value);
}
```

#### 4. AutoBlinkController (New)
**Responsibility:** Periodic automatic eye blinking

**Architecture Pattern:** Coroutine-based State Machine

```
States:
┌─────────────┐  Start  ┌─────────────┐  Wait  ┌─────────────┐
│    Idle     │ ──────> │   Waiting   │ ─────> │  Blinking   │
└─────────────┘         └─────────────┘        └─────────────┘
                              ↑                         │
                              └─────────────────────────┘
                                     Complete
```

**Delayed Auto-Start Pattern:**
```csharp
void Start() {
    shouldAutoStart = true;  // Mark intent
}

void Update() {
    // Delayed start: wait for Live2D init
    if (shouldAutoStart && CanStartBlinking()) {
        StartBlinking();
        shouldAutoStart = false;
    }
}

bool CanStartBlinking() {
    // Check faceController exists
    // Check parameters are accessible
    return faceController != null &&
           faceController.GetParameter(eyeParam) != -1f;
}
```

**Blink from Current State:**
```csharp
IEnumerator PerformBlink(bool isLeftEye, bool isBothEyes) {
    // Get current eye value (not fixed eyeOpenValue)
    float startValue = GetEyeValue(eyeParameter);

    // Close: startValue → closedValue
    // Open: closedValue → startValue

    // Ensures blink respects current eye state
}
```

**Features:**
- Sync or independent eye blinking
- Configurable frequency with random intervals
- AnimationCurve-based animation
- Close/open ratio control
- Blink strength (partial blinks)
- Real-time status monitoring

## Data Flow

### Normal Operation (Face Detected)

```
1. Webcam → MediaPipe
   ├─ Face landmarks detected
   ├─ 52 blendshapes extracted
   └─ Head rotation matrix → Euler angles

2. Python Smoothing (EMA)
   smoothed = α * current + (1-α) * previous

3. UDP Send (JSON)
   Message size: ~2KB
   Frequency: 30 FPS
   Latency: <5ms (localhost)

4. Unity Background Thread
   ├─ Receive UDP packet
   ├─ UTF-8 decode
   └─ Enqueue to ConcurrentQueue

5. Unity Main Thread (Update)
   ├─ Dequeue message
   ├─ Parse JSON (manual blendshapes extraction)
   └─ Invoke OnDataReceived event

6. Live2DFaceController
   ├─ For each ParameterMapping:
   │  ├─ Get source values
   │  ├─ Combine (if multiple)
   │  ├─ Transform (invert, remap, multiply, offset)
   │  ├─ Clamp
   │  ├─ Smooth (temporal)
   │  └─ SetParameter(live2DParam, value)
   └─ Update CubismModel

7. Live2D Rendering
   CubismModel applies deformers and renders
```

### No Face Detected

```
1. MediaPipe → No landmarks
2. Python sends: { faceDetected: false, blendshapes: {} }
3. Unity receives
4. Live2DFaceController → No parameter updates
5. AutoBlinkController (optional) → Provides idle blinking
```

## Threading Model

```
┌──────────────────────────────────────────────────────────────┐
│                        Unity Process                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Background Thread               Main Thread                 │
│  ┌──────────────┐                ┌──────────────┐            │
│  │ UDP Receive  │                │ Update()     │            │
│  │   Loop       │   Queue        │   Loop       │            │
│  │      ↓       │  ────────>     │      ↓       │            │
│  │ Enqueue(msg) │                │ Dequeue()    │            │
│  └──────────────┘                │      ↓       │            │
│                                   │ ProcessMsg() │            │
│                                   │      ↓       │            │
│                                   │ SetParameter │            │
│                                   └──────────────┘            │
│                                                               │
│  No shared mutable state except ConcurrentQueue              │
│  No locks needed (lock-free queue)                           │
└──────────────────────────────────────────────────────────────┘
```

## Configuration System

### Python Configuration (`config.json`)
```json
{
    "camera": {
        "index": 0,
        "width": 640,
        "height": 480,
        "fps": 30
    },
    "mediapipe": {
        "model_path": "models/face_landmarker_v2_with_blendshapes.task",
        "min_detection_confidence": 0.5,
        "min_tracking_confidence": 0.5
    },
    "network": {
        "host": "127.0.0.1",
        "port": 11111
    },
    "smoothing": {
        "alpha": 0.3
    }
}
```

### Unity Configuration (Inspector)
- **FaceDataReceiver**: Port, auto-start, queue size
- **Live2DFaceController**: Parameter mappings (list of ParameterMapping)
- **AutoBlinkController**: Blink frequency, animation, eye parameters

All configuration is Inspector-based (no code changes required).

## Error Handling

### Python Side
- Camera failure → Retry with exponential backoff
- MediaPipe model load failure → Exit with clear error
- Face not detected → Send `faceDetected: false`
- Network error → Log and continue (UDP is lossy)

### Unity Side
- JSON parse error → Log and skip message
- Parameter not found → Warn once (configurable)
- Thread exception → Log and restart thread
- Connection timeout → Fire OnConnectionLost event
- Live2D parameter invalid → Clamp to valid range

## Performance Characteristics

### Latency Budget
```
Webcam capture:        ~30ms  (1 frame @ 30 FPS)
MediaPipe processing:  ~15ms
Python smoothing:      <1ms
UDP transmission:      <5ms   (localhost)
Unity parsing:         <2ms
Unity parameter update: <1ms
Live2D rendering:      ~16ms  (60 FPS)
────────────────────────────
Total latency:         ~70ms
```

### Throughput
- Python: 30 FPS (33ms per frame)
- Network: ~2KB per message, 60 KB/s
- Unity: Processes up to 10 messages per Update (configurable)

### Memory
- Python: ~200MB (MediaPipe model)
- Unity: ~500MB (Live2D model + Unity runtime)
- Message queue: Max 10 messages (~20KB)

## Extensibility Points

### Adding New Parameters
1. MediaPipe extracts new blendshape automatically
2. Add to Unity ParameterMapping list in Inspector
3. No code changes required

### Custom Smoothing
```csharp
// Replace in Live2DFaceController
smoothedValue = CustomFilter(value, previousValue);
```

### Custom Combine Modes
```csharp
// Add to CombineMode enum and CombineValues method
case CombineMode.CustomWeightedAverage:
    return (values[0] * 0.7f + values[1] * 0.3f);
```

### Alternative Communication
- Replace NetworkSender with WebSocket/TCP sender
- Replace FaceDataReceiver UDP code
- Keep JSON format or switch to MessagePack

## Architecture Principles

1. **Separation of Concerns**
   - Python: Face tracking only
   - Unity: Animation control only
   - Network: Decoupled communication

2. **Event-Driven Design**
   - UnityEvents for loose coupling
   - Components subscribe to events
   - Easy to add new listeners

3. **Configuration over Code**
   - All mappings in Inspector
   - No recompilation for different models
   - Easy A/B testing

4. **Defensive Programming**
   - Thread-safe queues
   - Null checks everywhere
   - Graceful degradation (no face → idle animation)

5. **Performance First**
   - UDP for low latency
   - Background threads for I/O
   - Minimal allocations in Update loop
   - Manual JSON parsing (avoid reflection)

## Design Patterns Used

- **Producer-Consumer**: Background thread + ConcurrentQueue
- **Event Aggregator**: UnityEvent<FaceData>
- **Pipeline**: Multi-stage parameter transformation
- **Strategy**: Pluggable combine modes
- **State Machine**: AutoBlinkController coroutine states
- **Delayed Initialization**: Auto-start with condition checking
