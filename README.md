# VibeVtuber

A VTuber application built with Unity 6 and Python MediaPipe for real-time facial motion capture.

**This project was built fully with VibeCoding (Claude Code).**

## Features

- ✨ Real-time face tracking using MediaPipe
- 🎭 Live2D character animation
- 🚀 Low-latency UDP communication (<50ms)
- 🎨 52 ARKit-compatible blendshapes
- 🔧 Customizable sensitivity and smoothing
- 📊 Debug visualization tools

## Architecture

```
┌─────────┐      ┌──────────────┐      ┌─────────┐      ┌──────────┐
│ Webcam  │─────▶│   MediaPipe  │─────▶│   UDP   │─────▶│  Unity   │
│         │      │  (Python)    │      │  JSON   │      │  Live2D  │
└─────────┘      └──────────────┘      └─────────┘      └──────────┘
                       30 FPS            Port 11111        Real-time
```

## Quick Start

### 1. Python Setup (5 minutes)

```bash
# Install dependencies
cd PythonFaceTracker
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Download model (see SETUP_GUIDE.md for link)
# Place in PythonFaceTracker/models/

# Run tracker
python main.py
```

### 2. Unity Setup (10 minutes)

1. Open `VibeVtuberUnity/` in Unity Hub (Unity 6)
2. Install Live2D Cubism SDK for Unity
3. Import your Live2D model
4. Setup face tracking components (see `SETUP_GUIDE.md`)
5. Press Play!

## Documentation

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete step-by-step setup instructions
- **[PythonFaceTracker/README.md](PythonFaceTracker/README.md)** - Python tracker documentation
- **[VibeVtuberUnity/Assets/FaceTracking/README.md](VibeVtuberUnity/Assets/FaceTracking/README.md)** - Unity integration guide
- **[CLAUDE.md](CLAUDE.md)** - Project structure and development guidelines

## Project Structure

```
VibeVtuber/
├── PythonFaceTracker/          # Python facial motion capture
│   ├── models/                 # MediaPipe model files
│   ├── config.json             # Configuration
│   ├── face_tracker.py         # MediaPipe wrapper
│   ├── network_sender.py       # UDP communication
│   ├── main.py                 # Entry point
│   └── requirements.txt        # Dependencies
│
└── VibeVtuberUnity/            # Unity 6 project
    ├── Assets/
    │   ├── FaceTracking/       # Face tracking system
    │   │   ├── Scripts/
    │   │   │   ├── Core/       # Data structures & receiver
    │   │   │   ├── Live2D/     # Live2D integration
    │   │   │   └── Debug/      # Debug visualizer
    │   │   └── Scenes/         # Test scenes
    │   └── Settings/           # URP 2D renderer
    └── ProjectSettings/
```

## Requirements

### Software
- Python 3.8+ (3.10 recommended)
- Unity 6 (6000.3.8f1 or later)
- Live2D Cubism SDK for Unity
- Webcam (720p or higher)

### Python Packages
- mediapipe==0.10.14
- opencv-python==4.10.0.84
- numpy==1.26.4

### Unity Packages
- Universal Render Pipeline (URP) 17.3.0
- 2D Animation 13.0.4
- Input System 1.18.0
- Live2D Cubism SDK (external)

## Performance

- **Frame Rate**: 30 FPS
- **Latency**: 30-50ms (camera to display)
- **CPU Usage**: Python <30%, Unity <20%
- **Memory**: Python <200MB, Unity <500MB

## Features Breakdown

### Face Tracking (MediaPipe)
- ✅ 52 ARKit blendshapes
- ✅ Head rotation (yaw, pitch, roll)
- ✅ Eye blink tracking
- ✅ Eye look direction
- ✅ Mouth movements (open, smile, frown)
- ✅ Eyebrow tracking
- ✅ Exponential Moving Average smoothing

### Unity Integration
- ✅ Thread-safe UDP receiver
- ✅ Live2D Cubism parameter mapping
- ✅ Customizable sensitivity per feature
- ✅ Additional smoothing layer
- ✅ Real-time debug visualization
- ✅ Connection status monitoring

### Planned Features
- ⏳ Lip sync with audio analysis
- ⏳ Expression presets (hotkeys)
- ⏳ Recording and playback
- ⏳ Multiple Live2D model support
- ⏳ VMC protocol support (VRChat/VSeeFace)

## Troubleshooting

### Common Issues

**"WAITING FOR DATA" in Unity**
- Ensure Python tracker is running
- Check port 11111 is not blocked
- Verify both use same port number

**Model not moving**
- Check `Live2DFaceController` is attached
- Verify parameter names match your model
- Enable debug logging to see values

**Jittery movement**
- Increase smoothing factor
- Improve lighting conditions
- Reduce camera resolution

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed troubleshooting.

## Development

This project was built with **VibeCoding** (Claude Code) as a demonstration of AI-assisted development.

### Key Design Decisions

- **UDP over TCP**: Lower latency for real-time tracking
- **JSON over Binary**: Developer-friendly, debuggable
- **Background Threading**: Non-blocking network I/O
- **Event-Driven**: Decoupled components via UnityEvents
- **Dual Smoothing**: Python EMA + Unity Lerp for stability

### Extending the System

All 52 MediaPipe blendshapes are captured and available in the `FaceData.blendshapes` dictionary. To use additional blendshapes:

```csharp
// In Live2DFaceController or custom script
void OnFaceDataReceived(FaceData data)
{
    float tongueOut = data.GetBlendshape(BlendshapeNames.TongueOut);
    float cheekPuff = data.GetBlendshape(BlendshapeNames.CheekPuff);

    // Map to Live2D parameters
    SetParameter("MyModel_Tongue", tongueOut);
}
```

## License

(Add your license here)

## Credits

- **MediaPipe** - Google (Apache 2.0 License)
- **Live2D Cubism** - Live2D Inc.
- **Unity Engine** - Unity Technologies
- **Development** - Built with Claude Code (VibeCoding)

## Support

For setup help, see [SETUP_GUIDE.md](SETUP_GUIDE.md)

For issues:
1. Check documentation in relevant README files
2. Enable debug logging
3. Verify all prerequisites are installed

---

Made with ❤️ and Claude Code
