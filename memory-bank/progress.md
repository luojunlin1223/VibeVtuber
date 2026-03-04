# Progress

**Last Updated:** 2026-03-04

## Current Focus

朗读动画完整管线已上线并验证。所有语音（ISI + CosyVoice 自定义音色）统一走 Rhubarb 离线口型分析，session 持久化与重播已实现。

## Pipeline Status

```
Stage 1: Text → Qwen NLP → {emotion, intensity, blendshapes}    ✅ working
Stage 2: Text → TTS (ISI / CosyVoice) → audio WAV              ✅ working
Stage 3: WAV  → Rhubarb phonetic → mouth keyframes (A-H/X)     ✅ working
Stage 4: keyframes → UDP 11112 → Unity TextDrivenController     ✅ working
Session: audio + keyframes + emotion → disk JSON → replay       ✅ working
```

## Active Tasks

- **[TODO]** 打包测试：验证 macOS Release 包能正常接收 UDP 口型数据
- **[TODO]** 口型映射微调：根据实际模型效果调整 Rhubarb 各嘴形的 jawOpen/mouthFunnel 值
- RVC voice changer：full HuBERT + Faiss inference 仍是 stub（SimpleRVC pitch-shift 激活）
- BlackHole virtual audio：driver 已装，Core Audio 未加载

## Recent Completions (2026-03-04)

- ✅ **Rhubarb Lip Sync 集成**：v1.14.0 macOS 二进制，`PythonTextDriver/rhubarb`
  - `rhubarb_lipsync.py`：提取 keyframes，9 种嘴形 → Live2D blendshape 映射
  - `--recognizer phonetic`（语言无关，中文 TTS 音频有效）
  - ISI + CosyVoice 统一走 Rhubarb，失败时自动降级
- ✅ **CosyVoice WebSocket API 重写**：`tts_cosyvoice.py`
  - 原 dashscope HTTP SDK → WebSocket 原生协议
  - 格式：PCM 流式接收 + 手动构建 WAV 头
  - `word_timestamp_enabled=True`（克隆音色不支持，已有降级路径）
- ✅ **Session 持久化与重播**：`control-panel/data/sessions/*.json`
  - 每次朗读自动保存 audio_base64 + keyframes + emotion_bs
  - 控制面板历史列表，一键重播无需重新生成
  - API: `GET /api/sessions`, `POST /api/sessions/{id}/replay`, `DELETE /api/sessions/{id}`
- ✅ **TextDrivenController.cs 修复**
  - `ApplyZeros()`：reset / override 结束时主动把所有 Live2D 口型参数写零
  - override→false 过渡时也调用 ApplyZeros，防止嘴巴停在最后帧值
- ✅ **SpeechPlayer.py 修复**：`sender_thread.join(timeout=2.0)` 在 finally 前，消除 [Errno 9] Bad file descriptor
- ✅ **lip_sync.py 修复**：最后一个音素无条件插入关闭帧

## Recent Completions (2026-02-21 前)

- ✅ ISI TTS: AccessKey 永久鉴权（23h55m token 缓存，自动刷新）
- ✅ CosyVoice 声音复刻 CRUD 卡片
- ✅ 统一 TTS 音色下拉（ISI built-in + CosyVoice 自定义，自动路由）
- ✅ Qwen NLP 情感分析（Stage 1）
- ✅ ISI TTS 音素时间戳（Stage 2）
- ✅ RVC voice changer 模块（SimpleRVC 激活）
- ✅ 面部捕捉管线全面运行

## Key Architecture

### 朗读动画完整流程

```
用户输入文字
    ↓
[Qwen NLP] → emotion + intensity + emotion_bs
    ↓
[ISI TTS / CosyVoice WebSocket] → audio WAV
    ↓
[Rhubarb phonetic, ~0.5s] → mouth cues JSON
    ↓
[rhubarb_lipsync.py] → keyframes [{time_ms, blendshapes}]
    ↓
[SpeechPlayer] → sd.play(audio) + 定时 UDP 发送
    ↓
UDP port 11112 → [Unity TextDrivenController] → Live2D LateUpdate
    ↓
ParamMouthOpenY / ParamMouthForm 实时变化
```

### 降级策略（Rhubarb 失败时）

```
ISI  路径: phoneme_flat → phonemes_to_keyframes (ISI 音素 → viseme)
Cosy 路径: words (API 返回) → phoneme_flat → phonemes_to_keyframes
          或 _estimate_phoneme_flat (均匀分配 + 标点停顿估算)
```

### File Layout

```
PythonTextDriver/
├── text_analyzer.py        # Stage 1: Qwen NLP 情感分析
├── tts_isi.py              # Stage 2: ISI TTS + 音素时间戳 + token cache
├── tts_cosyvoice.py        # Stage 2: CosyVoice WebSocket TTS
├── lip_sync.py             # 音素 → Live2D viseme keyframes
├── rhubarb_lipsync.py      # Rhubarb 音频分析 → keyframes (统一口型)
├── speech_player.py        # 音频播放 + 定时 UDP 发送口型帧
├── rhubarb                 # Rhubarb v1.14.0 macOS 二进制
├── text_driver_config.json
└── main.py                 # 独立 NLP HTTP 服务（port 7778，控制面板不用）

control-panel/
├── server.py               # FastAPI 后端（speak-animate 统一走 Rhubarb）
├── static/index.html       # 前端（Alpine.js + TailwindCSS）
├── data/sessions/          # 朗读会话持久化 JSON
└── modules/

VibeVtuberUnity/Assets/FaceTracking/Scripts/
├── Core/FaceDataReceiver.cs        # UDP 11111 → 面部数据
├── Live2D/Live2DFaceController.cs  # Live2D 参数驱动
├── Live2D/AutoBlinkController.cs   # 自动眨眼
└── TextDriven/TextDrivenController.cs  # UDP 11112 → 口型/情感
```

### Control Panel API

```
POST /api/speak-animate          → 完整朗读动画（TTS + Rhubarb + 播放）
GET  /api/sessions               → 历史会话列表（不含音频/关键帧数据）
POST /api/sessions/{id}/replay   → 重播历史会话
DELETE /api/sessions/{id}        → 删除历史会话
POST /api/text-driver/speak      → {text} → Qwen NLP 情感分析
GET  /api/tts/meta               → 音色列表（ISI + CosyVoice）
POST /api/tts/synthesize         → TTS 合成（自动路由）
POST /api/voice-clone/upload     → 声音样本上传
POST /api/voice-clone/action     → CosyVoice 声音复刻 CRUD
POST /api/face-tracker/start|stop|restart
POST /api/unity/start|stop
```

### UDP 端口分配

| 端口 | 用途 | 发送方 | 接收方 |
|------|------|--------|--------|
| 11111 | 面部捕捉数据 | PythonFaceTracker | FaceDataReceiver.cs |
| 11112 | 口型/情感驱动 | SpeechPlayer.py | TextDrivenController.cs |

### How to Start

```bash
cd control-panel/
/opt/miniconda3/bin/conda run -n Vtuber python server.py
# → http://127.0.0.1:7777
```

### ADR Index

- ADR-001 — UDP+JSON for face tracking transport
- ADR-002 — Inspector-configurable Live2D parameter mappings
- ADR-003 — RVC for AI voice conversion
- ADR-004 — Rhubarb phonetic for audio-driven lip sync (language-agnostic)
