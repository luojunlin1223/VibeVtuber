"""
Aliyun ISI TTS with phoneme timestamps.

Token management: uses AccessKey ID + AccessKey Secret to auto-obtain and
cache tokens via nls.token.getToken(). Token is refreshed automatically when
it expires (no manual 24h renewal needed).

Returns:
  ok, audio_base64, phoneme_list (subtitles with per-character phoneme timing),
  plus raw metadata for debugging.

Docs:
  https://help.aliyun.com/zh/isi/developer-reference/timestamp-feature
"""

import base64
import json
import threading
import time
import nls
import nls.token

NLS_URL = "wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1"

# Common voices for ISI TTS
VOICES = [
    # ── 标准 ──
    {"id": "siyue",       "label": "思悦（女·标准）"},
    {"id": "xiaoyun",     "label": "小云（女·标准）"},
    {"id": "xiaogang",    "label": "小刚（男·标准）"},
    # ── 精品 ──
    {"id": "aijia",       "label": "爱嘉（女·温柔）"},
    {"id": "aiqi",        "label": "爱琪（女·甜美）"},
    {"id": "aida",        "label": "爱达（女·干练）"},
    {"id": "aicheng",     "label": "爱诚（男·稳重）"},
    {"id": "aishuo",      "label": "爱硕（男·磁性）"},
    # ── 多情感 ──
    {"id": "zhimiao_emo", "label": "知妙（女·多情感）"},
    {"id": "zhibing_emo", "label": "知冰（女·多情感）"},
    # ── 有声书 / 直播 ──
    {"id": "aiyuan",      "label": "爱媛（女·有声书）"},
    {"id": "aifan",       "label": "爱帆（男·直播）"},
    # ── 方言 ──
    {"id": "shanshan",    "label": "姗姗（女·粤语）"},
    {"id": "chuangirl",   "label": "川妹（女·四川话）"},
    # ── 英语 ──
    {"id": "Harry",       "label": "Harry（男·英文）"},
    {"id": "Stella",      "label": "Stella（女·英文）"},
]

# ---------------------------------------------------------------------------
# Token cache — shared across all synthesize() calls in the process lifetime.
# Re-fetches automatically when the token is within 60s of expiry.
# ---------------------------------------------------------------------------
_token_lock   = threading.Lock()
_cached_token: str  = ""
_token_expiry: float = 0.0   # Unix timestamp (seconds)
_TOKEN_MARGIN  = 60           # refresh this many seconds before actual expiry


def _get_token(ak_id: str, ak_secret: str) -> str:
    """Return a valid ISI token, fetching a new one when necessary."""
    global _cached_token, _token_expiry
    with _token_lock:
        if time.time() < _token_expiry - _TOKEN_MARGIN and _cached_token:
            return _cached_token
        print("[ISI TTS] fetching new token via AccessKey…")
        raw_token = nls.token.getToken(ak_id, ak_secret)
        # getToken returns only the token string; expiry unknown from return value.
        # ISI tokens last 24 h — cache for 23 h 55 min to stay safe.
        _cached_token = raw_token
        _token_expiry = time.time() + 23 * 3600 + 55 * 60
        print(f"[ISI TTS] token obtained (cached for ~24h): {raw_token[:8]}…")
        return _cached_token


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def synthesize(text: str, appkey: str, ak_id: str, ak_secret: str,
               voice: str = "siyue",
               url: str = NLS_URL) -> dict:
    """
    Synthesize speech with phoneme timestamps.

    Parameters:
      appkey    — ISI project AppKey
      ak_id     — Aliyun AccessKey ID   (long-term credential)
      ak_secret — Aliyun AccessKey Secret (long-term credential)

    Returns dict with:
      ok              bool
      audio_base64    str   (WAV, base64-encoded)
      audio_size      int   (bytes)
      subtitles       list  (per-character phoneme list)
      phoneme_flat    list  (all phonemes in order, for easy downstream use)
      elapsed_s       float
      request         dict  (echo of input params)
      error           str   (only when ok=False)
    """
    t0 = time.time()
    request_info = {
        "voice": voice,
        "text": text,
        "text_length": len(text),
        "url": url,
    }

    if not appkey:
        return {"ok": False, "error": "AppKey 未配置", "request": request_info}
    if not ak_id or not ak_secret:
        return {"ok": False, "error": "AccessKey ID 或 AccessKey Secret 未配置", "request": request_info}

    # Obtain (or reuse cached) token
    try:
        token = _get_token(ak_id, ak_secret)
    except Exception as e:
        return {"ok": False, "error": f"获取 Token 失败: {e}", "request": request_info,
                "elapsed_s": round(time.time() - t0, 3)}

    # Shared state collected via callbacks
    audio_chunks: list[bytes] = []
    subtitles: list[dict]     = []
    done_event       = threading.Event()
    completed_cleanly = threading.Event()
    error_holder: list[str]   = []

    def on_metainfo(message, *args):
        try:
            data = json.loads(message)
            payload = data.get("payload", data)
            subs = payload.get("subtitles", [])
            subtitles.extend(subs)
        except Exception as e:
            print(f"[ISI TTS] metainfo parse error: {e}")

    def on_data(data, *args):
        print(f"[ISI TTS] on_data: {len(data)} bytes")
        audio_chunks.append(data)

    def on_completed(message, *args):
        print(f"[ISI TTS] on_completed: {message}")
        completed_cleanly.set()
        try:
            data = json.loads(message)
            payload = data.get("payload", data)
            subs = payload.get("subtitles", [])
            if subs:
                subtitles.extend(subs)
        except Exception:
            pass
        done_event.set()

    def on_error(message, *args):
        print(f"[ISI TTS] on_error: {message}")
        error_holder.append(str(message))
        done_event.set()

    def on_close(*args):
        print(f"[ISI TTS] on_close, chunks so far: {len(audio_chunks)}")
        done_event.set()

    try:
        tts = nls.NlsSpeechSynthesizer(
            url=url,
            token=token,
            appkey=appkey,
            on_metainfo=on_metainfo,
            on_data=on_data,
            on_completed=on_completed,
            on_error=on_error,
            on_close=on_close,
        )
        tts.start(
            text,
            voice=voice,
            aformat="wav",
            wait_complete=True,
            ex={
                "enable_subtitle": True,
                "enable_phoneme_timestamp": True,
            },
        )
        done_event.wait(timeout=30)
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "request": request_info,
            "elapsed_s": round(time.time() - t0, 3),
        }

    if error_holder:
        return {
            "ok": False,
            "error": error_holder[0],
            "request": request_info,
            "elapsed_s": round(time.time() - t0, 3),
        }

    audio_bytes = b"".join(audio_chunks)
    print(f"[ISI TTS] done: {len(audio_chunks)} chunks, {len(audio_bytes)} bytes, {len(subtitles)} subtitles")

    if not completed_cleanly.is_set():
        return {
            "ok": False,
            "error": "连接被服务器关闭，未收到音频。请检查：① AppKey 是否正确 ② ISI 项目是否已开通 TTS 服务 ③ AccessKey 是否有 ISI 权限",
            "request": request_info,
            "elapsed_s": round(time.time() - t0, 3),
        }

    if not audio_bytes:
        return {
            "ok": False,
            "error": "合成完成但未收到音频数据",
            "request": request_info,
            "elapsed_s": round(time.time() - t0, 3),
        }

    phoneme_flat = []
    for sub in subtitles:
        for ph in sub.get("phoneme_list", []):
            phoneme_flat.append({
                "char":     sub.get("text", ""),
                "phoneme":  ph.get("phoneme", ""),
                "tone":     ph.get("tone", 0),
                "begin_ms": ph.get("begin_time", 0),
                "end_ms":   ph.get("end_time", 0),
            })

    return {
        "ok":            True,
        "request":       request_info,
        "audio_base64":  base64.b64encode(audio_bytes).decode(),
        "audio_size":    len(audio_bytes),
        "subtitles":     subtitles,
        "phoneme_flat":  phoneme_flat,
        "phoneme_count": len(phoneme_flat),
        "elapsed_s":     round(time.time() - t0, 3),
    }
