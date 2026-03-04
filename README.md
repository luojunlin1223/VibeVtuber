# VibeVtuber

A complete VTuber solution with real-time facial motion capture, AI-driven speech animation, and Live2D rendering.

**This project was built fully with VibeCoding (Claude Code).**

## Features

- ✨ **Real-time face tracking** — MediaPipe 52 ARKit blendshapes, 30 FPS
- 🎭 **Live2D character animation** — head rotation, eye, mouth, expression
- 🗣️ **Text-driven speech animation** — type text → AI generates voice + synced lip movement
- 🎤 **AI voice changer** — RVC (Retrieval-based Voice Conversion)
- 👄 **Accurate lip sync** — Rhubarb offline audio analysis, language-agnostic
- 🔊 **Custom voice cloning** — CosyVoice voice clone via DashScope
- 💾 **Session history** — every utterance saved, replay without re-generating
- 🖥️ **Web control panel** — browser-based management at localhost:7777
- 🚀 **Low-latency** — UDP communication, < 50ms face-to-render

## Architecture

```
┌─────────┐    ┌──────────────┐    ┌────────┐    ┌──────────────┐
│ Webcam  │───▶│  MediaPipe   │───▶│UDP     │───▶│  Unity       │
│         │    │  (Python)    │    │11111   │    │  Live2D      │
└─────────┘    └──────────────┘    └────────┘    └──────────────┘
                    30 FPS          face data       face params

┌─────────┐    ┌──────────────────────────────────┐    ┌────────┐    ┌──────────────┐
│  Text   │───▶│  Control Panel (FastAPI)          │───▶│UDP     │───▶│  Unity       │
│  Input  │    │  Qwen NLP → emotion               │    │11112   │    │  TextDriven  │
│         │    │  ISI/CosyVoice TTS → WAV          │    └────────┘    └──────────────┘
└─────────┘    │  Rhubarb → mouth keyframes        │    mouth+emotion   Live2D params
               │  SpeechPlayer → local audio       │
               └──────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   Web Control Panel (http://localhost:7777)       │
│  Face Tracker │ Unity Manager │ Speech Animate │ History │ Logs  │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Start control panel
cd control-panel
/opt/miniconda3/bin/conda run -n Vtuber python server.py
# → open http://localhost:7777
```

In Unity, attach `TextDrivenController.cs` to the same GameObject as `Live2DFaceController`.

## Project Structure

```
VibeVtuber/
├── control-panel/                  # Web control panel (FastAPI + Alpine.js)
│   ├── server.py                   # Backend API + speak-animate pipeline
│   ├── static/index.html           # Frontend UI
│   ├── data/sessions/              # Persisted TTS sessions (audio + keyframes)
│   └── modules/
│       ├── process_manager.py
│       └── config_manager.py
│
├── PythonFaceTracker/              # Real-time face capture
│   ├── face_tracker.py             # MediaPipe wrapper
│   ├── network_sender.py           # UDP sender → port 11111
│   ├── config.json
│   └── main.py
│
├── PythonTextDriver/               # Text-driven animation engine
│   ├── text_analyzer.py            # Qwen NLP → emotion / intensity
│   ├── tts_isi.py                  # Aliyun ISI TTS + phoneme timestamps
│   ├── tts_cosyvoice.py            # CosyVoice WebSocket TTS
│   ├── lip_sync.py                 # Phoneme → Live2D viseme keyframes
│   ├── rhubarb_lipsync.py          # Rhubarb audio analysis → keyframes
│   ├── speech_player.py            # Audio playback + timed UDP → port 11112
│   └── rhubarb                     # Rhubarb v1.14.0 binary (macOS)
│
└── VibeVtuberUnity/                # Unity 6 Live2D renderer
    └── Assets/FaceTracking/Scripts/
        ├── Core/FaceDataReceiver.cs          # UDP 11111 receiver
        ├── Live2D/Live2DFaceController.cs    # Live2D parameter driver
        ├── Live2D/AutoBlinkController.cs     # Auto blink
        └── TextDriven/TextDrivenController.cs # UDP 11112 → mouth/emotion
```

## Text-Driven Speech Animation

Type any text in the control panel → the character speaks with lip-synced animation.

**Pipeline:**
1. **Qwen NLP** analyzes emotion (happy / sad / angry / …) and intensity
2. **TTS synthesis** — Aliyun ISI (built-in voices) or CosyVoice (cloned voices)
3. **Rhubarb** analyzes the audio offline, outputs 9 mouth shapes (A–H / X) with millisecond timestamps
4. **SpeechPlayer** plays audio locally while sending timed UDP frames to Unity
5. **Unity** applies mouth parameters to the Live2D model in `LateUpdate()`

**Session history:** every utterance is saved to `control-panel/data/sessions/`. Replay any session with one click — no re-generation needed.

## UDP Protocol

| Port | Direction | Content |
|------|-----------|---------|
| 11111 | Python → Unity | Face tracking blendshapes (30 FPS) |
| 11112 | Python → Unity | Lip-sync keyframes + emotion blendshapes (event-based) |

Message format:
```json
{"type": "lip_sync",    "blendshapes": {"jawOpen": 0.8, "mouthFunnel": 0.0}}
{"type": "text_emotion","blendshapes": {"mouthSmileLeft": 0.6, ...}}
{"type": "reset",       "blendshapes": {}}
```

## Requirements

### Software
- Python 3.11 (conda env `Vtuber`)
- Unity 6 (6000.3.8f1+)
- Live2D Cubism SDK for Unity
- Odin Inspector (Unity Asset Store)
- Webcam (720p+)

### API Keys (for speech animation)
- Aliyun ISI: AppKey + AccessKey ID + AccessKey Secret
- DashScope (Qwen + CosyVoice): API Key

## Performance

| Component | Target | Actual |
|-----------|--------|--------|
| Face tracking | 30 FPS | 30 FPS |
| Face→render latency | < 50ms | ~30ms |
| Rhubarb analysis | — | ~0.5s per utterance |
| TTS synthesis | — | 1–3s (ISI/CosyVoice) |

## Planned / In Progress

- ⏳ RVC full inference (HuBERT + Faiss) — currently SimpleRVC pitch-shift
- ⏳ Expression presets (hotkeys)
- ⏳ Multi Live2D model support
- ⏳ VMC protocol (VRChat / VSeeFace)

## Key Design Decisions

- **UDP over TCP**: Lower latency, fire-and-forget suits animation frames
- **Rhubarb phonetic**: Language-agnostic audio analysis — works for Chinese TTS without phoneme dictionary
- **Session JSON**: Full audio + keyframes persisted; replay costs zero API calls
- **Dual UDP ports**: Face capture (11111) and text-driven (11112) are independent, can coexist
- **MonoBehaviour only**: Never SerializedMonoBehaviour — compatibility and portability

## Credits

- **MediaPipe** — Google (Apache 2.0)
- **Live2D Cubism** — Live2D Inc.
- **Rhubarb Lip Sync** — Daniel S. Wolf (MIT)
- **Unity Engine** — Unity Technologies
- **Built with** — Claude Code (VibeCoding)
