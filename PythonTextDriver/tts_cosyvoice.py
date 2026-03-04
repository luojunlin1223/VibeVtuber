"""
CosyVoice TTS synthesis for custom cloned voices.

Uses the CosyVoice WebSocket API (dashscope) with word_timestamp_enabled=True
so that character-level timestamps are returned and can drive Live2D lip-sync.

Protocol:
  1. Connect  wss://dashscope.aliyuncs.com/api-ws/v1/inference
  2. run-task  (model, voice, format=pcm, word_timestamp_enabled=true)
  3. task-started  → continue-task (text) + finish-task
  4. result-generated → binary PCM chunks
  5. task-finished   → words array with begin_time / end_time per character
  6. Build proper WAV from raw PCM, convert words → phoneme_flat
"""

import base64
import json
import struct
import time
import uuid

import websocket  # websocket-client (installed as dashscope dependency)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

_KNOWN_MODELS = [
    "cosyvoice-v3.5-plus",
    "cosyvoice-v3.5-flash",
    "cosyvoice-v3-plus",
    "cosyvoice-v3-flash",
    "cosyvoice-v2",
    "cosyvoice-v1",
]

# PCM output parameters (must match what we tell the API)
_SAMPLE_RATE = 22050
_CHANNELS    = 1
_BITS        = 16


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_model(voice_id: str) -> str:
    """Derive synthesis model from a CosyVoice custom voice_id."""
    for m in _KNOWN_MODELS:
        if voice_id.startswith(m + "-") or voice_id == m:
            return m
    return "cosyvoice-v2"  # safe fallback


def _estimate_phoneme_flat(text: str, pcm_bytes: bytes) -> list:
    """
    Fallback when word_timestamp_enabled is unsupported (e.g. cloned voices).

    Distributes speech characters across the audio duration, inserting
    proportional silent gaps at punctuation positions so the mouth closes
    naturally during pauses.
    """
    # Weight of each punctuation mark as a fraction of one character slot
    PAUSE_W = {
        '、': 0.5, '：': 0.5, '·': 0.3,
        '，': 0.8, '；': 0.8, ',': 0.8, ';': 0.8,
        '。': 1.5, '！': 1.5, '？': 1.5, '.': 1.5, '!': 1.5, '?': 1.5,
        '…': 2.0, '—': 1.0,
    }

    # Build a weighted sequence of ('speech', char) | ('pause', weight)
    items = []
    for c in text:
        if c in PAUSE_W:
            # Merge consecutive pauses
            if items and items[-1][0] == 'pause':
                items[-1] = ('pause', items[-1][1] + PAUSE_W[c])
            else:
                items.append(['pause', PAUSE_W[c]])
        elif c.strip():
            items.append(('speech', c))

    speech_items = [it for it in items if it[0] == 'speech']
    if not speech_items:
        return []

    total_weight  = sum(1 if t == 'speech' else w for t, w in items)
    bytes_per_ms  = _SAMPLE_RATE * _CHANNELS * (_BITS // 8) / 1000
    total_ms      = len(pcm_bytes) / bytes_per_ms
    lead_in_ms    = min(80, total_ms * 0.05)
    speech_ms     = total_ms - lead_in_ms
    ms_per_weight = speech_ms / total_weight

    result   = []
    cursor   = lead_in_ms

    for item in items:
        item_type, value = item[0], item[1]
        if item_type == 'speech':
            slot     = ms_per_weight
            begin_ms = int(cursor)
            # Occupy 65% of the slot; the 35% gap triggers a closing frame
            end_ms   = int(cursor + slot * 0.65)
            result.append({
                "char":     value,
                "phoneme":  "e",
                "begin_ms": begin_ms,
                "end_ms":   end_ms,
            })
            cursor += slot
        else:
            # Pause: advance cursor without adding a speech entry
            cursor += ms_per_weight * value

    return result


def _build_wav(pcm_bytes: bytes,
               sample_rate: int = _SAMPLE_RATE,
               channels: int   = _CHANNELS,
               bits: int       = _BITS) -> bytes:
    """Wrap raw PCM bytes in a standard 44-byte WAV/RIFF header."""
    data_size  = len(pcm_bytes)
    byte_rate  = sample_rate * channels * bits // 8
    block_align = channels * bits // 8
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size,
        b"WAVE",
        b"fmt ", 16,
        1,                   # PCM audio format
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        b"data", data_size,
    )
    return header + pcm_bytes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def synthesize(text: str, voice_id: str, api_key: str) -> dict:
    """
    Synthesize text with a CosyVoice custom voice via WebSocket API.

    Returns dict compatible with tts_isi.synthesize():
      ok              bool
      audio_base64    str    WAV, base64-encoded
      audio_size      int
      phoneme_flat    list   [{char, phoneme, begin_ms, end_ms}, ...]
      phoneme_count   int
      elapsed_s       float
      request         dict
      error           str    (only on failure)
    """
    t0 = time.time()
    model     = _extract_model(voice_id)
    task_id   = str(uuid.uuid4())
    request_info = {
        "voice_id": voice_id, "model": model,
        "text": text, "text_length": len(text),
    }

    if not api_key:
        return {"ok": False, "error": "Qwen API Key 未配置", "request": request_info}

    pcm_chunks: list[bytes] = []
    words: list[dict]       = []
    error_msg: list[str]    = [None]   # list so closures can mutate

    # ------------------------------------------------------------------
    # WebSocket callbacks
    # ------------------------------------------------------------------

    def _on_open(ws):
        run_task = {
            "header": {
                "action": "run-task",
                "task_id": task_id,
                "streaming": "duplex",
            },
            "payload": {
                "task_group": "audio",
                "task":       "tts",
                "function":   "SpeechSynthesizer",
                "model":      model,
                "parameters": {
                    "text_type":              "PlainText",
                    "voice":                  voice_id,
                    "format":                 "pcm",
                    "sample_rate":            _SAMPLE_RATE,
                    "word_timestamp_enabled": True,
                },
                "input": {},
            },
        }
        ws.send(json.dumps(run_task))

    def _on_message(ws, message):
        # Binary frames = raw PCM audio
        if isinstance(message, bytes):
            pcm_chunks.append(message)
            return

        # Text frames = JSON control events
        try:
            data  = json.loads(message)
        except Exception:
            return

        event = data.get("header", {}).get("event", "")

        if event == "task-started":
            # Send the text to synthesize
            ws.send(json.dumps({
                "header": {
                    "action": "continue-task",
                    "task_id": task_id,
                    "streaming": "duplex",
                },
                "payload": {"input": {"text": text}},
            }))
            # Signal end of input immediately (short text = single message)
            ws.send(json.dumps({
                "header": {
                    "action": "finish-task",
                    "task_id": task_id,
                    "streaming": "duplex",
                },
                "payload": {"input": {}},
            }))

        elif event == "result-generated":
            # Audio data arrives as binary frames (handled above).
            # This text event just marks a generation checkpoint — ignore.
            pass

        elif event == "task-finished":
            w = (data.get("payload", {})
                     .get("output", {})
                     .get("sentence", {})
                     .get("words", []))
            words.extend(w)
            ws.close()

        elif event == "task-failed":
            hdr = data.get("header", {})
            error_msg[0] = (
                hdr.get("message") or
                hdr.get("status_text") or
                "task-failed (no message)"
            )
            ws.close()

    def _on_error(ws, error):
        # Only record if we don't already have a richer task-failed message
        if not error_msg[0]:
            error_msg[0] = str(error)

    # ------------------------------------------------------------------
    # Run WebSocket (blocking)
    # ------------------------------------------------------------------
    ws_app = websocket.WebSocketApp(
        _WS_URL,
        header={"Authorization": f"Bearer {api_key}"},
        on_open=_on_open,
        on_message=_on_message,
        on_error=_on_error,
    )
    ws_app.run_forever()

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------
    if error_msg[0]:
        return {
            "ok":       False,
            "error":    error_msg[0],
            "request":  request_info,
            "elapsed_s": round(time.time() - t0, 3),
        }

    if not pcm_chunks:
        return {
            "ok":       False,
            "error":    "合成完成但未收到音频数据",
            "request":  request_info,
            "elapsed_s": round(time.time() - t0, 3),
        }

    # ------------------------------------------------------------------
    # Build WAV from raw PCM
    # ------------------------------------------------------------------
    pcm_bytes = b"".join(pcm_chunks)
    wav_bytes = _build_wav(pcm_bytes)

    # ------------------------------------------------------------------
    # Lip-sync: return phoneme_flat so server.py can run Rhubarb or fall back.
    # word_timestamp_enabled gives character-level timestamps when supported;
    # _estimate_phoneme_flat is the last-resort uniform distribution.
    # ------------------------------------------------------------------
    if words:
        phoneme_flat = [
            {
                "char":     w.get("text", ""),
                "phoneme":  "e",
                "begin_ms": w.get("begin_time", 0),
                "end_ms":   w.get("end_time",   0),
            }
            for w in words
            if w.get("end_time", 0) > w.get("begin_time", 0)
        ]
    else:
        phoneme_flat = _estimate_phoneme_flat(text, pcm_bytes)

    return {
        "ok":            True,
        "request":       request_info,
        "audio_base64":  base64.b64encode(wav_bytes).decode(),
        "audio_size":    len(wav_bytes),
        "phoneme_flat":  phoneme_flat,
        "phoneme_count": len(phoneme_flat),
        "elapsed_s":     round(time.time() - t0, 3),
    }
