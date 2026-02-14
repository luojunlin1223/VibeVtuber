# Technology Stack

**Last Updated:** 2026-02-15 01:03

## Overview

VibeVtuber uses a dual-language architecture: Python for face tracking (ML-optimized) and Unity/C# for rendering and animation control.

## Python Stack

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **mediapipe** | 0.10.30 | Face tracking with ARKit blendshapes |
| **opencv-python** | 4.10.0.84 | Webcam capture and frame processing |
| **numpy** | 1.26.4 | Matrix operations for head rotation |

### Python Runtime
- **Version**: Python 3.8+ (tested on 3.11)
- **Environment**: Virtual environment (`venv`)
- **Platform**: Windows, macOS, Linux

### MediaPipe Details
- **Model**: Face Landmarker v2 with blendshapes
- **File**: `face_landmarker_v2_with_blendshapes.task`
- **Size**: ~10MB
- **Features**:
  - 468 face landmarks
  - 52 ARKit-compatible blendshapes
  - 4x4 transformation matrix (head pose)
  - Real-time video mode

### Networking
- **Protocol**: UDP (fire-and-forget)
- **Port**: 11111 (localhost only)
- **Serialization**: JSON (UTF-8)
- **Socket**: `socket.SOCK_DGRAM` (non-blocking)

## Unity Stack

### Unity Engine
- **Version**: Unity 6 (6000.3.8f1)
- **Template**: 2D (URP)
- **API Level**: .NET Standard 2.1
- **Platform**: Windows (primary), macOS/Linux compatible

### Render Pipeline
- **Pipeline**: Universal Render Pipeline (URP)
- **Version**: 17.3.0
- **Renderer**: 2D Renderer
- **Assets**:
  - `UniversalRenderPipelineAsset.asset`
  - `Renderer2D.asset`

### Unity Packages

| Package | Version | Purpose |
|---------|---------|---------|
| **2D Animation** | 13.0.4 | Sprite rigging and animation |
| **2D Sprite** | 1.0.0 | Sprite management |
| **2D Tilemap** | 1.0.0 | Level design (future) |
| **Input System** | 1.18.0 | New input system |
| **Timeline** | 1.8.10 | Cinematic sequences |
| **Visual Scripting** | 1.9.9 | Node-based scripting |
| **Test Framework** | 1.4.6 | Unit/integration tests |

### Third-Party Packages

| Package | Purpose | Vendor |
|---------|---------|--------|
| **Live2D Cubism SDK** | Live2D model rendering | Live2D Inc. |
| **Odin Inspector** | Advanced Inspector UI | Sirenix |

### C# Scripting

#### Core Namespaces
```csharp
using System;
using System.Collections.Concurrent;  // Thread-safe queue
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using UnityEngine.Events;
using Sirenix.OdinInspector;           // UI framework
using Live2D.Cubism.Core;              // Live2D
using Live2D.Cubism.Framework;
```

#### Language Features Used
- **Threading**: Background thread for UDP I/O
- **Generics**: `List<T>`, `Dictionary<K,V>`, `ConcurrentQueue<T>`
- **LINQ**: `Array.Find()`, `List.ForEach()`
- **Coroutines**: `IEnumerator` for auto-blink
- **Events**: `UnityEvent<T>` for decoupling
- **Attributes**: Odin Inspector annotations

### Networking (Unity Side)
- **Class**: `System.Net.Sockets.UdpClient`
- **Mode**: Asynchronous receive (background thread)
- **Deserialization**: Manual JSON parsing (no JsonUtility for dictionaries)
- **Thread Safety**: `ConcurrentQueue<string>` for message passing

## Live2D Integration

### Live2D Cubism SDK
- **Version**: 4.x (latest)
- **Components**:
  - `CubismModel`: Model container
  - `CubismParameter`: Animatable parameters
  - `CubismDeformer`: Mesh deformation
- **Parameter Types**:
  - Angles (head rotation): -30° to +30°
  - Normalized (blendshapes): 0.0 to 1.0

### Parameter Naming Conventions
**Standard Cubism Parameters:**
- `ParamAngleX/Y/Z`: Head rotation
- `ParamEyeLOpen/ROpen`: Eye opening
- `ParamEyeBallX/Y`: Eye direction
- `ParamBrowLY/RY`: Eyebrow height
- `ParamMouthOpenY`: Mouth opening
- `ParamMouthForm`: Mouth shape (smile/frown)

**Custom Parameters:**
- Model-specific names vary
- Inspector configuration required

## Odin Inspector Framework

### Purpose
Professional-grade Unity Inspector customization

### Key Features Used
- **Attributes**:
  - `[Title]`: Section headers
  - `[BoxGroup]`: Visual grouping
  - `[FoldoutGroup]`: Collapsible sections
  - `[HorizontalGroup]`: Horizontal layout
  - `[ProgressBar]`: Visual value bars
  - `[LabelText]`: Custom labels
  - `[Tooltip]`: Hover hints
  - `[ShowIf]`: Conditional display
  - `[Button]`: Inspector buttons
  - `[GUIColor]`: Custom colors
  - `[ReadOnly]`: Non-editable fields
  - `[SuffixLabel]`: Units display

### Base Classes
- `SerializedMonoBehaviour`: Odin-enhanced MonoBehaviour
- Supports more serialization types (Dictionary, etc.)

## Development Tools

### IDEs
- **Primary**: Visual Studio Code
- **Alternative**: Visual Studio 2022
- **Unity**: Built-in script editor

### Version Control
- **Git**: Source control
- **GitHub**: Remote repository
- **LFS**: Large file storage (Live2D models)

### Debugging Tools
- **Unity Console**: Runtime logging
- **Unity Profiler**: Performance analysis
- **Python Print**: Debug output
- **Wireshark**: Network packet inspection (optional)

## File Formats

### Configuration
- **Python Config**: `config.json` (JSON)
- **Unity Settings**: `ProjectSettings/` (YAML)

### Assets
- **Live2D Model**: `.model3.json` + `.moc3` + textures
- **Animation Curve**: Unity `AnimationCurve` (serialized)
- **Sprites**: PNG (for future 2D sprites)

### Data Exchange
- **Network**: JSON (UTF-8 encoded)
- **Message Size**: ~2KB per frame
- **Frequency**: 30 messages/second

### Documentation
- **Format**: Markdown (`.md`)
- **Location**: Project root and subdirectories

## Build & Deployment

### Python Deployment
```bash
# Virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Unix

# Dependencies
pip install -r requirements.txt

# Model download
# Manual: Download face_landmarker_v2_with_blendshapes.task
# Place in: PythonFaceTracker/models/
```

### Unity Deployment
- **Build Target**: Windows Standalone (64-bit)
- **Build Location**: `Builds/`
- **Dependencies**: Live2D SDK included in build

### Distribution
- **Python**: Standalone executable (future: PyInstaller)
- **Unity**: Executable + Data folder
- **Total Size**: ~500MB (Unity build) + ~50MB (Python)

## Performance Targets

### Python Performance
- **Target FPS**: 30
- **CPU Usage**: <30%
- **Memory**: <200MB
- **Startup Time**: <3 seconds

### Unity Performance
- **Target FPS**: 60 (rendering)
- **Data Processing**: 30 messages/second
- **CPU Usage**: <20% (Update loop)
- **Memory**: <500MB
- **Latency**: <50ms (camera to render)

## Platform Support

### Officially Tested
- ✅ Windows 11 (primary development)
- ✅ Python 3.11
- ✅ Unity 6

### Expected to Work
- ⚠️ macOS (Intel/Apple Silicon)
- ⚠️ Linux (Ubuntu 22.04+)
- ⚠️ Python 3.8-3.12

### Known Limitations
- Webcam required (no video file input yet)
- Localhost only (no remote tracking)
- Single face tracking (multi-face not supported)

## Future Technology Considerations

### Potential Additions
- **MessagePack**: Binary serialization (smaller than JSON)
- **WebSocket**: Bidirectional communication
- **gRPC**: Structured RPC (if needed)
- **SQLite**: Recording/playback storage
- **FFmpeg**: Video file input/output

### Optimization Opportunities
- **IL2CPP**: Unity scripting backend (AOT compilation)
- **Burst Compiler**: High-performance C# code
- **GPU Compute**: MediaPipe on GPU
- **One-Euro Filter**: Better smoothing algorithm

## Dependencies Management

### Python
```
requirements.txt
├─ mediapipe==0.10.30
├─ opencv-python==4.10.0.84
└─ numpy==1.26.4
```

### Unity
```
Packages/manifest.json
├─ com.unity.2d.animation@13.0.4
├─ com.unity.inputsystem@1.18.0
├─ com.unity.render-pipelines.universal@17.3.0
└─ [Live2D Cubism SDK - imported manually]
```

### External
- Live2D Cubism SDK: Downloaded from Live2D website
- Odin Inspector: Asset Store purchase
- MediaPipe Model: Downloaded from MediaPipe website

## Security Considerations

### Network Security
- Localhost only (127.0.0.1)
- No authentication (local machine trust)
- UDP fire-and-forget (no replay attacks)

### Data Privacy
- No data sent outside local machine
- No telemetry
- Webcam access required (user must consent)

### Code Security
- No eval() or dynamic code execution
- No user input in shell commands
- Type-safe parameter access
