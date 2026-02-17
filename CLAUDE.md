# CLAUDE.md - Project Configuration for Claude Code

## Python Environment

**CRITICAL**: All Python commands must be run with the `Vtuber` conda environment activated.

Before running any Python scripts in `PythonFaceTracker/`, always activate the conda environment:

```bash
conda activate Vtuber
```

### Running Python Scripts

When using the Bash tool to run Python scripts, always prefix with conda activation:

```bash
# Example: Running the face tracker
conda activate Vtuber && cd PythonFaceTracker && python main.py

# Example: Running camera detection
conda activate Vtuber && cd PythonFaceTracker && python list_cameras.py
```

## Project Structure

```
VibeVtuber/
├── PythonFaceTracker/          # Python face tracking (MediaPipe)
│   ├── main.py                 # Main entry point
│   ├── face_tracker.py         # MediaPipe integration
│   ├── network_sender.py       # UDP sender
│   ├── list_cameras.py         # Camera detection tool
│   └── config.json             # Configuration file
│
├── VibeVtuberUnity/            # Unity Live2D controller
│   └── Assets/
│       └── FaceTracking/
│           └── Scripts/
│               ├── Core/
│               │   └── FaceDataReceiver.cs
│               └── Live2D/
│                   ├── Live2DFaceController.cs
│                   └── AutoBlinkController.cs
│
└── memory-bank/                # Project memory (progress, architecture, decisions)
```

## Common Tasks

### Camera Configuration

To list all available cameras:
```bash
conda activate Vtuber && cd PythonFaceTracker && python list_cameras.py
```

Then update the camera index in `PythonFaceTracker/config.json`.

### Running the Face Tracker

```bash
conda activate Vtuber && cd PythonFaceTracker && python main.py
```

### Unity Development

Open `VibeVtuberUnity/` in Unity 6 (6000.3.8f1).

## Unity Coding Standards

### CRITICAL: MonoBehaviour Usage

**ALWAYS use `MonoBehaviour`, NEVER use `SerializedMonoBehaviour`**

```csharp
// ✅ CORRECT - Use standard MonoBehaviour
using UnityEngine;
using Sirenix.OdinInspector;

public class MyScript : MonoBehaviour
{
    [Title("Settings")]
    [BoxGroup("Group")]
    public int myValue;
}
```

```csharp
// ❌ WRONG - Do NOT use SerializedMonoBehaviour
using Sirenix.OdinInspector;

public class MyScript : SerializedMonoBehaviour  // NEVER DO THIS
{
    // ...
}
```

**Reasoning:**
- `MonoBehaviour` is Unity's standard base class
- `SerializedMonoBehaviour` from Odin Inspector can cause compatibility issues
- Standard `MonoBehaviour` works perfectly with Odin Inspector attributes
- Keeps code portable and maintainable

**When Writing/Editing Unity Scripts:**
1. Always inherit from `MonoBehaviour`
2. Use Odin Inspector attributes (`[Title]`, `[BoxGroup]`, etc.) directly with `MonoBehaviour`
3. If you see `SerializedMonoBehaviour` in existing code, replace it with `MonoBehaviour`

## Dependencies

- **Python**: Managed via conda environment `Vtuber`
  - mediapipe
  - opencv-python
  - numpy

- **Unity**: Unity 6 with URP
  - Live2D Cubism SDK
  - Odin Inspector (for Inspector attributes only, NOT SerializedMonoBehaviour)
