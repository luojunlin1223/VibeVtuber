"""
VibeVtuber Control Panel - FastAPI backend
Run: python server.py
Then open http://localhost:7777 in your browser.
"""

import asyncio
import base64
import datetime
import json
import os
import sys
import time
import uuid

import httpx
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "PythonTextDriver"))

from modules.process_manager import ProcessManager, discover_apps, PROJECT_ROOT
from modules.config_manager import (
    read_tracker_config,
    write_tracker_config,
    read_panel_config,
    write_panel_config,
    read_text_driver_config,
    write_text_driver_config,
)
from text_analyzer import TextAnalyzer
from tts_isi import synthesize as _tts_synthesize_isi, VOICES as TTS_VOICES
from tts_cosyvoice import synthesize as _tts_synthesize_cosy
from lip_sync import phonemes_to_keyframes
from rhubarb_lipsync import extract_keyframes as _rhubarb_extract
from speech_player import SpeechPlayer

_speech_player = SpeechPlayer()

proc_manager = ProcessManager()
_clients: list[WebSocket] = []

STATIC_DIR   = os.path.join(os.path.dirname(__file__), "static")
UPLOADS_DIR  = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

DATA_DIR     = os.path.join(os.path.dirname(__file__), "data")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

COSYVOICE_API = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"


# ---------------------------------------------------------------------------
# WebSocket broadcast helpers
# ---------------------------------------------------------------------------

async def _broadcast(message: dict):
    for client in _clients[:]:
        try:
            await client.send_json(message)
        except Exception:
            _clients.remove(client)


async def _status_loop():
    """Periodically push process status and buffered logs to all clients."""
    while True:
        await _broadcast({
            "type": "status",
            "face_tracker": proc_manager.is_running("face_tracker"),
            "unity": proc_manager.is_running("unity"),
        })

        for line in proc_manager.drain_logs("face_tracker"):
            await _broadcast({"type": "log", "source": "face_tracker", "data": line})

        await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_status_loop())
    yield
    proc_manager.stop("face_tracker")
    proc_manager.stop("unity")


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return FileResponse(
        os.path.join(STATIC_DIR, "index.html"),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/config")
async def get_config():
    return {
        "tracker": read_tracker_config(),
        "panel": read_panel_config(),
        "text_driver": read_text_driver_config(),
    }


@app.post("/api/config")
async def update_config(body: dict):
    if "tracker" in body:
        write_tracker_config(body["tracker"])
    if "panel" in body:
        write_panel_config(body["panel"])
    if "text_driver" in body:
        write_text_driver_config(body["text_driver"])
    return {"ok": True}


# Face tracker
@app.post("/api/face-tracker/start")
async def face_tracker_start():
    ok = proc_manager.start_face_tracker()
    return {"ok": ok}


@app.post("/api/face-tracker/stop")
async def face_tracker_stop():
    ok = proc_manager.stop("face_tracker")
    return {"ok": ok}


@app.post("/api/face-tracker/restart")
async def face_tracker_restart():
    proc_manager.stop("face_tracker")
    await asyncio.sleep(0.8)
    ok = proc_manager.start_face_tracker()
    return {"ok": ok}


# Text driver — runs inline in the control panel process, no subprocess
@app.post("/api/text-driver/speak")
async def text_driver_speak(body: dict):
    text = (body.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "text 不能为空"}

    cfg = read_text_driver_config()
    qwen = cfg.get("qwen", {})
    api_key = qwen.get("api_key", "").strip()
    if not api_key:
        return {"ok": False, "error": "请先填写 Qwen API Key"}

    analyzer = TextAnalyzer(
        api_key=api_key,
        model=qwen.get("model", "qwen-turbo"),
        base_url=qwen.get("base_url",
                           "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, analyzer.analyze, text)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# TTS (Aliyun ISI + CosyVoice custom voices)
@app.get("/api/tts/meta")
async def tts_meta():
    voices = [dict(v, custom=False, source="isi") for v in TTS_VOICES]

    # Append custom CosyVoice voices if API key is available
    api_key = _cosyvoice_api_key()
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    COSYVOICE_API,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "voice-enrollment", "input": {"action": "list_voice", "page_index": 0, "page_size": 100}},
                )
            if resp.status_code == 200:
                data = resp.json()
                for v in (data.get("output") or {}).get("voice_list", []):
                    if v.get("status") == "OK":
                        voices.append({
                            "id":     v["voice_id"],
                            "label":  v["voice_id"],
                            "custom": True,
                            "source": "cosyvoice",
                        })
        except Exception:
            pass  # custom voices unavailable, return ISI voices only

    return {"voices": voices}


@app.post("/api/tts/synthesize")
async def tts_synthesize(body: dict):
    text = (body.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "text 不能为空"}

    voice = body.get("voice", "siyue")

    # Route custom CosyVoice voices to CosyVoice synthesis
    if str(voice).startswith("cosyvoice-"):
        api_key = _cosyvoice_api_key()
        if not api_key:
            return {"ok": False, "error": "请先在文本驱动模块填写 Qwen API Key"}
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _tts_synthesize_cosy, text, voice, api_key)

    # ISI TTS for built-in voices
    cfg = read_text_driver_config()
    isi = cfg.get("isi", {})
    appkey    = isi.get("appkey",    "").strip()
    ak_id     = isi.get("ak_id",     "").strip()
    ak_secret = isi.get("ak_secret", "").strip()
    if not appkey or not ak_id or not ak_secret:
        return {"ok": False, "error": "请先填写 ISI AppKey、AccessKey ID 和 AccessKey Secret"}

    url = isi.get("url", "wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _tts_synthesize_isi, text, appkey, ak_id, ak_secret, voice, url)


# Speak + animate: combines emotion analysis + TTS + lip-sync + audio playback
@app.post("/api/speak-animate")
async def speak_animate(body: dict):
    text = (body.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "text 不能为空"}

    voice = body.get("voice", "siyue")
    cfg   = read_text_driver_config()

    # 1. Emotion analysis (optional — skipped if no API key)
    emotion    = "neutral"
    intensity  = 0.5
    emotion_bs = {}

    qwen    = cfg.get("qwen", {})
    api_key = qwen.get("api_key", "").strip()
    if api_key:
        analyzer = TextAnalyzer(
            api_key=api_key,
            model=qwen.get("model", "qwen-turbo"),
            base_url=qwen.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
        loop = asyncio.get_event_loop()
        try:
            result     = await loop.run_in_executor(None, analyzer.analyze, text)
            emotion    = result.get("emotion", "neutral")
            intensity  = result.get("intensity", 0.5)
            emotion_bs = result.get("blendshapes", {})
        except Exception as e:
            print(f"[speak-animate] emotion analysis error: {e}")

    # 2. TTS synthesis — route CosyVoice custom voices or ISI built-in voices
    loop = asyncio.get_event_loop()
    if str(voice).startswith("cosyvoice-"):
        cosy_api_key = _cosyvoice_api_key()
        if not cosy_api_key:
            return {"ok": False, "error": "请先在文本驱动模块填写 Qwen API Key（用于 CosyVoice 合成）"}
        tts_result = await loop.run_in_executor(None, _tts_synthesize_cosy, text, voice, cosy_api_key)
    else:
        isi       = cfg.get("isi", {})
        appkey    = isi.get("appkey",    "").strip()
        ak_id     = isi.get("ak_id",     "").strip()
        ak_secret = isi.get("ak_secret", "").strip()
        if not appkey or not ak_id or not ak_secret:
            return {"ok": False, "error": "请先填写 ISI AppKey、AccessKey ID 和 AccessKey Secret"}
        url = isi.get("url", "wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1")
        tts_result = await loop.run_in_executor(
            None, _tts_synthesize_isi, text, appkey, ak_id, ak_secret, voice, url
        )
    if not tts_result.get("ok"):
        return {"ok": False, "error": tts_result.get("error", "TTS 合成失败")}

    # 3. Generate lip-sync keyframes
    # Always try Rhubarb first (audio-based, works for ISI and CosyVoice alike).
    # Fall back to phoneme_flat (ISI) or estimation (CosyVoice) when unavailable.
    audio_b64    = tts_result.get("audio_base64", "")
    phoneme_flat = tts_result.get("phoneme_flat", [])

    rhubarb_kfs, rhubarb_dur = await loop.run_in_executor(
        None, _rhubarb_extract, base64.b64decode(audio_b64)
    )

    if rhubarb_kfs is not None:
        keyframes   = rhubarb_kfs
        duration_ms = rhubarb_dur
    else:
        keyframes   = tts_result.get("keyframes") or phonemes_to_keyframes(phoneme_flat)
        duration_ms = (tts_result.get("duration_ms")
                       or (phoneme_flat[-1]["end_ms"] if phoneme_flat else 0))

    # 4. Play audio + send UDP animation frames in a background thread (non-blocking)
    audio_b64 = tts_result.get("audio_base64", "")

    def _play():
        _speech_player.play(audio_b64, keyframes, emotion_bs)

    loop.run_in_executor(None, _play)

    # Save session to disk
    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    session_data = {
        "id": session_id, "text": text, "voice": voice,
        "emotion": emotion, "intensity": intensity,
        "duration_ms": duration_ms,
        "audio_size": tts_result.get("audio_size", 0),
        "phoneme_count": len(phoneme_flat), "keyframe_count": len(keyframes),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "audio_base64": audio_b64, "keyframes": keyframes, "emotion_bs": emotion_bs,
    }
    with open(os.path.join(SESSIONS_DIR, f"{session_id}.json"), "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False)

    return {
        "ok":            True,
        "session_id":    session_id,
        "emotion":       emotion,
        "intensity":     intensity,
        "phoneme_count": len(phoneme_flat),
        "keyframe_count": len(keyframes),
        "audio_size":    tts_result.get("audio_size", 0),
        "duration_ms":   duration_ms,
        "voice":         voice,
    }


@app.get("/api/sessions")
async def list_sessions():
    sessions = []
    for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(SESSIONS_DIR, fname), encoding="utf-8") as f:
            d = json.load(f)
        sessions.append({k: v for k, v in d.items()
                         if k not in ("audio_base64", "keyframes", "emotion_bs")})
    return {"sessions": sessions}


@app.post("/api/sessions/{session_id}/replay")
async def replay_session(session_id: str):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return {"ok": False, "error": "会话不存在"}
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, lambda: _speech_player.play(
        d["audio_base64"], d["keyframes"], d["emotion_bs"]))
    return {"ok": True, "session_id": session_id, "duration_ms": d.get("duration_ms", 0)}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(path):
        os.remove(path)
    return {"ok": True}


# CosyVoice voice clone management
@app.post("/api/voice-clone/upload")
async def voice_clone_upload(file: UploadFile = File(...)):
    """Save uploaded audio to static/uploads/ and return its served URL."""
    ext = os.path.splitext(file.filename or "audio")[1] or ".wav"
    filename = f"{int(time.time() * 1000)}{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    return {
        "ok": True,
        "filename": filename,
        "local_url": f"/static/uploads/{filename}",
        "size": len(content),
    }


def _cosyvoice_api_key() -> str:
    return read_text_driver_config().get("qwen", {}).get("api_key", "").strip()


@app.post("/api/voice-clone/action")
async def voice_clone_action(body: dict):
    """Proxy CosyVoice clone CRUD actions to DashScope API."""
    api_key = _cosyvoice_api_key()
    if not api_key:
        return {"ok": False, "error": "请先在文本驱动模块填写 Qwen API Key"}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            COSYVOICE_API,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
    data = resp.json()
    if resp.status_code != 200:
        return {"ok": False, "error": data.get("message", f"HTTP {resp.status_code}"), "raw": data}
    return {"ok": True, **data}


# Unity app
async def unity_discover():
    apps = discover_apps()
    return {"apps": apps}


@app.post("/api/unity/start")
async def unity_start(body: dict):
    path = body.get("path") or read_panel_config().get("unity_app_path", "")
    if not path:
        return {"ok": False, "error": "未配置 Unity 应用路径"}
    ok, error = proc_manager.start_unity(path)
    return {"ok": ok, "error": error}


@app.post("/api/unity/stop")
async def unity_stop():
    ok = proc_manager.stop("unity")
    return {"ok": ok}


# WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _clients:
            _clients.remove(websocket)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host, port = "127.0.0.1", 7777
    print(f"\n  VibeVtuber Control Panel")
    print(f"  ─────────────────────────────────")
    print(f"  http://{host}:{port}")
    print(f"  ─────────────────────────────────")
    print(f"  Ctrl+C 停止服务\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")
