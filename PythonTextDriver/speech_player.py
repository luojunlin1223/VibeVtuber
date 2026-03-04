"""
SpeechPlayer: plays TTS audio locally via sounddevice while sending timed
UDP blendshape frames to Unity on port 11112.

Alignment strategy:
  - Prepend AUDIO_PAD_MS ms of silence to the WAV so the device buffer
    is warm before the first phoneme arrives.
  - keyframe send time = T0 + AUDIO_PAD_MS/1000 + keyframe.time_ms/1000
  - T0 is recorded immediately after sounddevice.play() is called.
  - time.perf_counter() gives sub-millisecond precision; localhost UDP
    adds < 1 ms latency, so total alignment error is typically < 5 ms.
"""

import base64
import io
import json
import socket
import threading
import time

try:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf
    _HAS_AUDIO = True
except ImportError:
    _HAS_AUDIO = False

UDP_HOST     = "127.0.0.1"
UDP_PORT     = 11112
AUDIO_PAD_MS = 200   # ms of silence prepended for device warm-up


def _prepend_silence(audio_bytes: bytes, pad_ms: int) -> tuple:
    """
    Prepend pad_ms milliseconds of silence to a WAV byte buffer.

    Returns (padded_ndarray, samplerate).
    """
    buf = io.BytesIO(audio_bytes)
    with sf.SoundFile(buf) as f:
        samplerate = f.samplerate
        channels   = f.channels
        data       = f.read(dtype="float32")

    pad_samples = int(samplerate * pad_ms / 1000)
    if channels > 1:
        silence = np.zeros((pad_samples, channels), dtype="float32")
    else:
        silence = np.zeros((pad_samples,), dtype="float32")

    padded = np.concatenate([silence, data])
    return padded, samplerate


def _send_udp(sock: socket.socket, payload: dict):
    """Send a JSON payload as a single UDP datagram to Unity."""
    msg = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        sock.sendto(msg, (UDP_HOST, UDP_PORT))
    except Exception as e:
        print(f"[SpeechPlayer] UDP send error: {e}")


class SpeechPlayer:
    """Plays audio locally and sends timed UDP frames to Unity."""

    def play(self, audio_b64: str, keyframes: list, emotion_bs: dict) -> None:
        """
        Play audio locally and send timed blendshape frames to Unity.

        This method blocks until audio playback is complete.
        Call from a background executor thread to avoid blocking the
        FastAPI event loop.

        Args:
            audio_b64:   Base64-encoded WAV bytes from ISI TTS.
            keyframes:   List of {time_ms, blendshapes} from lip_sync.
            emotion_bs:  Emotion blendshapes dict (mouthSmileLeft, etc.)
                         from TextAnalyzer. Sent immediately at T0.
        """
        if not _HAS_AUDIO:
            print("[SpeechPlayer] sounddevice/soundfile/numpy not installed — skipping audio")
            return

        if not audio_b64:
            print("[SpeechPlayer] no audio data provided")
            return

        raw_wav = base64.b64decode(audio_b64)

        try:
            padded_audio, samplerate = _prepend_silence(raw_wav, AUDIO_PAD_MS)
        except Exception as e:
            print(f"[SpeechPlayer] WAV decode error: {e}")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        pad_s = AUDIO_PAD_MS / 1000.0

        try:
            # Send emotion blendshapes immediately (before audio starts)
            if emotion_bs:
                _send_udp(sock, {"type": "text_emotion", "blendshapes": emotion_bs})

            # Start audio playback and mark T0
            sd.play(padded_audio, samplerate)
            t0 = time.perf_counter()

            # Send lip-sync keyframes from a background thread
            def _sender():
                for kf in keyframes:
                    target_t = t0 + pad_s + kf["time_ms"] / 1000.0
                    delay = target_t - time.perf_counter()
                    if delay > 0:
                        time.sleep(delay)
                    _send_udp(sock, {"type": "lip_sync", "blendshapes": kf["blendshapes"]})

            sender_thread = threading.Thread(target=_sender, daemon=True)
            sender_thread.start()

            # Block until audio finishes, then wait for last keyframe to be sent
            # before closing the socket (prevents [Errno 9] and out-of-order resets)
            sd.wait()
            sender_thread.join(timeout=2.0)

        finally:
            # Always send reset frame so Unity reverts to face-capture mode
            reset_bs = {
                "jawOpen":         0.0,
                "mouthFunnel":     0.0,
                "mouthPucker":     0.0,
                "mouthSmileLeft":  0.0,
                "mouthSmileRight": 0.0,
                "mouthFrownLeft":  0.0,
                "mouthFrownRight": 0.0,
            }
            _send_udp(sock, {"type": "reset", "blendshapes": reset_bs})
            sock.close()
