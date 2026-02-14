# VibeVtuber Python Face Tracker

Real-time facial motion capture using MediaPipe, sending data to Unity via UDP.

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Download MediaPipe Model

Download the MediaPipe face landmarker model file:
- **Model**: `face_landmarker_v2_with_blendshapes.task`
- **URL**: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task

Place the downloaded file in the `models/` directory.

### 3. Configure Settings

Edit `config.json` to adjust:
- Camera settings (index, resolution, FPS)
- Network settings (host, port)
- MediaPipe confidence thresholds
- Smoothing parameters

## Usage

```bash
# Ensure virtual environment is activated
venv\Scripts\activate  # Windows

# Run the face tracker
python main.py
```

### Keyboard Controls
- **q** - Quit application
- **s** - Toggle debug window on/off

## Architecture

- **face_tracker.py** - MediaPipe Face Landmarker wrapper, processes webcam frames
- **network_sender.py** - UDP socket communication to Unity
- **main.py** - Main loop (capture → process → send)
- **config.json** - Configuration parameters

## Output Data Format

JSON sent via UDP to Unity:

```json
{
  "timestamp": 1234567890.123,
  "faceDetected": true,
  "headRotation": {
    "yaw": 15.5,
    "pitch": -10.2,
    "roll": 2.1
  },
  "blendshapes": {
    "eyeBlinkLeft": 0.0,
    "eyeBlinkRight": 0.1,
    "jawOpen": 0.45,
    ... (52 total ARKit blendshapes)
  }
}
```

## Troubleshooting

**Camera not found:**
- Check camera index in `config.json` (try 0, 1, 2)
- Ensure camera is not in use by another application

**Model file error:**
- Verify model file is in `models/` directory
- Check file name matches exactly: `face_landmarker_v2_with_blendshapes.task`

**Poor performance:**
- Reduce camera resolution in `config.json`
- Lower MediaPipe confidence thresholds
- Ensure good lighting on face

**Jittery tracking:**
- Increase smoothing alpha value (try 0.5)
- Ensure stable lighting conditions
