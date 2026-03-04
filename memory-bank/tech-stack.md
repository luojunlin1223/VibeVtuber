# Technology Stack

**Last Updated:** 2026-03-04

## Overview

VibeVtuber uses a dual-language architecture: Python for face tracking and text-driven animation (ML-optimized), Unity/C# for Live2D rendering.

## Python Stack

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **mediapipe** | 0.10.30 | Face tracking with ARKit blendshapes |
| **opencv-python** | 4.10.0.84 | Webcam capture and frame processing |
| **numpy** | 1.26.4 | Matrix operations for head rotation |

### Control Panel Dependencies (conda env: Vtuber)

| Package | Purpose |
|---------|---------|
| **fastapi** | REST API + WebSocket server |
| **uvicorn** | ASGI server |
| **httpx** | Async HTTP client (CosyVoice clone API proxy) |
| **python-multipart** | File upload support (voice clone audio) |
| **openai** | Qwen NLP via OpenAI-compat API |
| **dashscope** | Qwen TTS + CosyVoice synthesis |
| **alibabacloud-nls-python-sdk** | ISI TTS WebSocket SDK (`import nls`) |
| **aliyun-python-sdk-core** | ISI AccessKey → Token exchange |
| **websocket-client** | CosyVoice WebSocket API raw protocol |
| **sounddevice** | 本地音频播放（TTS 朗读）|
| **soundfile** | WAV 文件解码 |

### External Binaries

| Binary | Version | Purpose |
|--------|---------|---------|
| **rhubarb** | v1.14.0 | 离线音频口型分析，`PythonTextDriver/rhubarb` |

### External AI Services

| Service | SDK / Protocol | Purpose |
|---------|---------------|---------|
| **Qwen (DashScope)** | openai-compat REST | NLP emotion analysis |
| **Aliyun ISI TTS** | WebSocket (NLS) | Speech synthesis + phoneme timestamps |
| **CosyVoice (DashScope)** | WebSocket raw protocol | Custom voice clone synthesis |
| **CosyVoice Clone API** | REST via httpx | Create/list/query/delete custom voices |

### Python Runtime
- **Version**: Python 3.11
- **Environment**: conda `Vtuber`
- **Platform**: macOS (primary), Linux compatible

### MediaPipe Details
- **Model**: Face Landmarker v2 with blendshapes
- **Features**: 468 landmarks, 52 ARKit blendshapes, head pose matrix, real-time video

### Networking
- **Face tracking**: UDP 11111, localhost, 30 msg/s, JSON
- **Text-driven animation**: UDP 11112, localhost, event-based, JSON

## Text-Driven Animation Stack

### Pipeline

```
Text → Qwen NLP → emotion_bs
Text → ISI/CosyVoice TTS → WAV audio
WAV  → Rhubarb (phonetic) → mouth cues (A-H/X + timestamps)
     → Live2D keyframes [{time_ms, blendshapes}]
     → SpeechPlayer → sd.play() + timed UDP → Unity
```

### Rhubarb Lip Sync

- **Binary**: `PythonTextDriver/rhubarb` (v1.14.0, macOS)
- **Mode**: `--recognizer phonetic`（纯声学分析，无语言限制）
- **Output**: 9 种嘴形（X 静默 / A 闭口 / B-H 开口程度递增 / E 圆唇）
- **Latency**: ~0.5s per short utterance
- **Fallback**: ISI phoneme_flat → phonemes_to_keyframes（Rhubarb 不可用时）

### Rhubarb 嘴形 → Live2D 映射

| Shape | 发音特征 | jawOpen | mouthFunnel |
|-------|---------|---------|-------------|
| X | 静默 | 0.00 | 0.00 |
| A | P/B/M 闭口 | 0.05 | 0.00 |
| B | K/S/T 微开 | 0.25 | 0.00 |
| C | TH/CH 中开 | 0.40 | 0.00 |
| D | "A" 大开 | 0.80 | 0.00 |
| E | "O" 圆唇 | 0.50 | 0.65 |
| F | F/V 齿唇 | 0.15 | 0.00 |
| G | L 舌尖 | 0.30 | 0.00 |
| H | 放松开口 | 0.35 | 0.00 |

### CosyVoice WebSocket 协议

- **Endpoint**: `wss://dashscope.aliyuncs.com/api-ws/v1/inference`
- **Auth**: `Authorization: Bearer {api_key}` header
- **Audio format**: PCM 22050Hz mono 16bit（手动添加 WAV header）
- **word_timestamp_enabled**: 仅系统音色支持，克隆音色返回空 words

### Session 持久化

- **路径**: `control-panel/data/sessions/{id}.json`
- **内容**: text, voice, emotion, audio_base64, keyframes, emotion_bs, metadata
- **重播**: 直接读取 JSON 调用 SpeechPlayer，无需重新合成

## Unity Stack

### Unity Engine
- **Version**: Unity 6 (6000.3.8f1)
- **Template**: 2D (URP)
- **API Level**: .NET Standard 2.1

### Unity Packages

| Package | Version | Purpose |
|---------|---------|---------|
| **Universal Render Pipeline** | 17.3.0 | 渲染管线 |
| **2D Animation** | 13.0.4 | Sprite rigging |
| **Input System** | 1.18.0 | 输入系统 |
| **Live2D Cubism SDK** | 4.x | Live2D 模型渲染 |
| **Odin Inspector** | latest | Inspector UI 增强 |

### C# Scripts

| 脚本 | 端口 | 职责 |
|------|------|------|
| `FaceDataReceiver.cs` | 11111 | 接收面部捕捉 blendshapes |
| `Live2DFaceController.cs` | — | Live2D 参数驱动（含 SetParameter API）|
| `AutoBlinkController.cs` | — | 自动眨眼 |
| `TextDrivenController.cs` | 11112 | 接收口型/情感，LateUpdate 写 Live2D |

### TextDrivenController 设计要点

- `LateUpdate()` 处理 UDP 消息队列，写 Live2D 参数
- `resetDelay = 0.3s`：超过此时间无新帧则停止 override
- `ApplyZeros()`：reset 消息或 override 结束时主动清零所有参数
- 消息类型：`lip_sync`（口型帧）、`text_emotion`（情感 blendshapes）、`reset`（归位）

### Coding Standards
- **ALWAYS** `MonoBehaviour`，**NEVER** `SerializedMonoBehaviour`
- Odin Inspector 属性直接加在 `MonoBehaviour` 上

### Live2D Parameter Conventions
- `ParamMouthOpenY`: 嘴巴张开度（jawOpen 驱动）
- `ParamMouthForm`: 嘴型（mouthFunnel/mouthPucker/mouthSmile 驱动）
- `ParamAngleX/Y/Z`: 头部旋转（面部捕捉驱动）

## Development Tools

### IDEs
- Visual Studio Code + Claude Code

### Version Control
- Git + GitHub

### Debugging
- Unity Console, Python print, Wireshark (optional)

## Platform Support

### Officially Tested
- ✅ macOS (Apple Silicon / Intel)
- ✅ Python 3.11 (conda Vtuber)
- ✅ Unity 6 (6000.3.8f1)

### Known Limitations
- CosyVoice 克隆音色不支持 `word_timestamp_enabled`（API 限制）
- Rhubarb phonetic 模式中文精度低于英文，但对 TTS 干净音频效果可接受
- RVC 全量推理（HuBERT + Faiss）尚未实现，当前用 SimpleRVC pitch-shift
