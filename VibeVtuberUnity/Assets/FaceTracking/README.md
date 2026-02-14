# FaceTracking System for VibeVtuber

Unity-side implementation for receiving face tracking data from Python MediaPipe tracker and controlling Live2D models.

## Architecture

```
Python MediaPipe → UDP (JSON) → FaceDataReceiver → Live2DFaceController → Live2D Model
                                        ↓
                                 DebugFaceVisualizer
```

## Scripts Overview

### Core/
- **FaceData.cs** - Data structures for face tracking (matches Python JSON format)
- **FaceDataReceiver.cs** - UDP receiver with thread-safe message queue

### Live2D/
- **Live2DFaceController.cs** - Maps MediaPipe blendshapes to Live2D parameters

### Debug/
- **DebugFaceVisualizer.cs** - Real-time debug UI (toggle with F1)

## Setup Instructions

### 1. Prerequisites
- Live2D Cubism SDK for Unity installed
- Live2D model imported into Unity project
- Python face tracker running (see `PythonFaceTracker/README.md`)

### 2. Scene Setup

#### Option A: Manual Setup
1. Create new scene or open existing scene
2. Add your Live2D model to the scene (should have `CubismModel` component)
3. Create empty GameObject named "FaceTrackingManager"
4. Add `FaceDataReceiver` component to FaceTrackingManager
   - Set Port to 11111 (must match Python config)
   - Enable "Auto Start"
5. Add `Live2DFaceController` component to your Live2D model GameObject
   - Drag FaceTrackingManager to the "Data Receiver" field
   - OR: FaceDataReceiver's `OnDataReceived` event will auto-wire if in same scene
6. (Optional) Create UI Canvas and add `DebugFaceVisualizer` component
   - Assign FaceDataReceiver reference
   - Press F1 in Play mode to toggle debug display

#### Option B: Using Prefabs (TODO)
1. Drag `FaceTrackingManager.prefab` into scene
2. Add your Live2D model
3. Assign references in Inspector

### 3. Component Configuration

#### FaceDataReceiver Settings
- **Port**: 11111 (default, matches Python config)
- **Auto Start**: Enabled (starts receiving on Play)
- **Max Queue Size**: 10 (prevents memory overflow)
- **Log Errors**: Enabled for debugging

#### Live2DFaceController Settings
- **Head Rotation Sensitivity**: 1.0 (adjust if model over/under-rotates)
- **Eye Sensitivity**: 1.0
- **Mouth Sensitivity**: 1.0
- **Eyebrow Sensitivity**: 1.0
- **Smoothing Factor**: 0.3 (0 = instant, 1 = very smooth)
- **Max Yaw/Pitch/Roll**: 30° (prevents extreme rotations)

#### DebugFaceVisualizer Settings
- **Toggle Key**: F1
- **Start Visible**: True
- **Show All Blendshapes**: False (shows only priority parameters)

## Testing Workflow

### Quick Test (without Live2D model)
1. Start Python tracker: `python main.py`
2. Enter Play mode in Unity
3. Add `DebugFaceVisualizer` to scene
4. Press F1 to show debug UI
5. Verify:
   - Status shows "CONNECTED"
   - FPS displays ~30
   - Latency <50ms
   - Head rotation values update when you move
   - Blendshape values change with facial expressions

### Full Test (with Live2D model)
1. Start Python tracker
2. Enter Play mode
3. Move head → model rotates
4. Blink eyes → model blinks
5. Open mouth → model mouth opens
6. Smile → model smiles

## Live2D Parameter Mapping

The system maps MediaPipe blendshapes to standard Live2D parameters:

| Facial Feature | MediaPipe Blendshape | Live2D Parameter | Notes |
|---------------|---------------------|------------------|-------|
| Head Yaw | headRotation.yaw | ParamAngleX | Left/right |
| Head Pitch | headRotation.pitch | ParamAngleY | Up/down |
| Head Roll | headRotation.roll | ParamAngleZ | Tilt |
| Left Eye Blink | eyeBlinkLeft | ParamEyeLOpen | Inverted |
| Right Eye Blink | eyeBlinkRight | ParamEyeROpen | Inverted |
| Eye Look X | eyeLook* | ParamEyeBallX | Combined |
| Eye Look Y | eyeLook* | ParamEyeBallY | Combined |
| Mouth Open | jawOpen | ParamMouthOpenY | Direct |
| Smile/Frown | mouthSmile/Frown | ParamMouthForm | Difference |
| Eyebrows | browInnerUp | ParamBrowLY/RY | Combined |

### Custom Model Parameters

If your Live2D model uses different parameter names:
1. Open your model in Live2D Viewer to see available parameters
2. Edit `Live2DFaceController.cs`
3. Modify the `SetParameter()` calls in each Apply* method

Example:
```csharp
// Change from standard parameter name
SetParameter("ParamEyeLOpen", leftEyeOpen);

// To your model's custom name
SetParameter("MyModel_LeftEye", leftEyeOpen);
```

## Troubleshooting

### "WAITING FOR DATA" in Debug UI
- Ensure Python tracker is running
- Check port matches (11111 in both Python config.json and Unity)
- Verify firewall isn't blocking localhost UDP
- Check Console for errors

### Model Not Moving
- Verify `Live2DFaceController` is attached to model GameObject
- Check FaceDataReceiver reference is assigned
- Enable "Log Parameter Updates" in Live2DFaceController to see which parameters are being set
- Verify your model has standard Live2D parameters (ParamAngleX, ParamEyeLOpen, etc.)

### Jittery Movement
- Increase Smoothing Factor (try 0.5-0.7)
- Reduce sensitivity multipliers
- Check Python smoothing alpha in config.json

### Wrong Rotation Direction
- Multiply sensitivity by -1 (e.g., set to -1.0 instead of 1.0)
- Some models have inverted axis

### Mouth Not Opening Enough
- Increase Mouth Sensitivity (try 1.5-2.0)
- Check if your model's ParamMouthOpenY has correct min/max range

## Performance

Expected performance:
- **Frame Rate**: 30 FPS data reception
- **Latency**: <50ms (camera → Unity)
- **CPU Usage**: <5% on main thread
- **Memory**: Minimal (queue size limited to 10 messages)

If experiencing lag:
- Check Unity Profiler (Window > Analysis > Profiler)
- Reduce Python camera resolution
- Lower smoothing factor for faster response

## Advanced Features

### Recording Face Data
(TODO: Implement JSON recording/playback)

### Expression Presets
(TODO: Keyboard hotkeys for preset expressions)

### Multiple Models
(TODO: Support switching Live2D models at runtime)

## API Reference

### FaceDataReceiver Events

```csharp
// Called when new face data arrives (~30 times per second)
OnDataReceived.AddListener((FaceData data) => {
    Debug.Log($"Face detected: {data.faceDetected}");
});

// Called when connection is established
OnConnectionEstablished.AddListener(() => {
    Debug.Log("Connected to Python tracker");
});

// Called when no data received for 2 seconds
OnConnectionLost.AddListener(() => {
    Debug.Log("Lost connection to Python tracker");
});
```

### FaceData API

```csharp
void OnFaceDataReceived(FaceData data)
{
    // Check if face is detected
    if (!data.faceDetected) return;

    // Access head rotation
    float yaw = data.headRotation.yaw;
    float pitch = data.headRotation.pitch;
    float roll = data.headRotation.roll;

    // Access blendshapes by name
    float eyeBlink = data.GetBlendshape(BlendshapeNames.EyeBlinkLeft);
    float mouthOpen = data.GetBlendshape(BlendshapeNames.JawOpen);

    // Check if blendshape exists
    if (data.HasBlendshape("customBlendshape"))
    {
        float value = data.GetBlendshape("customBlendshape");
    }
}
```

## License

Part of VibeVtuber project. See main repository for license information.
