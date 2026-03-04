"""
Rhubarb Lip Sync integration.

Runs the rhubarb binary with --recognizer phonetic (language-agnostic,
works for Chinese TTS audio) and converts the mouth cue output to
Live2D blendshape keyframes compatible with speech_player.SpeechPlayer.

Rhubarb mouth shapes → Live2D mapping:
  X  silence / rest       jawOpen=0.00
  A  P / B / M (closed)   jawOpen=0.05
  B  K / S / T / D / N    jawOpen=0.25
  C  TH / CH / SH         jawOpen=0.40
  D  "A" vowel, wide       jawOpen=0.80
  E  "O" vowel, round      jawOpen=0.50  mouthFunnel=0.65
  F  F / V (teeth-lip)     jawOpen=0.15
  G  L / tongue             jawOpen=0.30
  H  relaxed open           jawOpen=0.35
"""

import json
import os
import subprocess
import tempfile

_RHUBARB = os.path.join(os.path.dirname(__file__), "rhubarb")

# Blendshape targets per Rhubarb mouth shape
_SHAPE_BS: dict[str, dict[str, float]] = {
    "X": {"jawOpen": 0.00, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "A": {"jawOpen": 0.05, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "B": {"jawOpen": 0.25, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "C": {"jawOpen": 0.40, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "D": {"jawOpen": 0.80, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "E": {"jawOpen": 0.50, "mouthFunnel": 0.65, "mouthPucker": 0.00},
    "F": {"jawOpen": 0.15, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "G": {"jawOpen": 0.30, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "H": {"jawOpen": 0.35, "mouthFunnel": 0.00, "mouthPucker": 0.00},
}
_SILENT = _SHAPE_BS["X"]


def extract_keyframes(wav_bytes: bytes, timeout: int = 30) -> tuple[list[dict], int] | tuple[None, int]:
    """
    Analyse WAV audio with Rhubarb and return (keyframes, duration_ms).

    keyframes: list of {"time_ms": int, "blendshapes": dict}
                one entry per mouth-cue start time.
                Rhubarb covers the full audio with consecutive cues
                (X for silence, A-H for speech), so the last cue naturally
                closes the mouth.

    Returns (None, 0) on any failure so the caller can fall back gracefully.
    """
    if not os.path.isfile(_RHUBARB):
        print(f"[Rhubarb] binary not found at {_RHUBARB}")
        return None, 0

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path  = os.path.join(tmpdir, "audio.wav")
        json_path = os.path.join(tmpdir, "cues.json")

        with open(wav_path, "wb") as f:
            f.write(wav_bytes)

        try:
            proc = subprocess.run(
                [
                    _RHUBARB,
                    "--recognizer", "phonetic",   # language-agnostic
                    "--exportFormat", "json",
                    "--quiet",
                    "-o", json_path,
                    wav_path,
                ],
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            print(f"[Rhubarb] timed out after {timeout}s")
            return None, 0
        except FileNotFoundError as e:
            print(f"[Rhubarb] cannot execute binary: {e}")
            return None, 0

        if proc.returncode != 0:
            err = proc.stderr.decode(errors="replace").strip()
            print(f"[Rhubarb] exit {proc.returncode}: {err}")
            return None, 0

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[Rhubarb] failed to parse output: {e}")
            return None, 0

    cues     = data.get("mouthCues", [])
    duration_ms = int(data.get("metadata", {}).get("duration", 0) * 1000)

    keyframes = []
    for cue in cues:
        shape    = cue.get("value", "X")
        start_ms = int(round(cue["start"] * 1000))
        bs       = dict(_SHAPE_BS.get(shape, _SILENT))
        keyframes.append({"time_ms": start_ms, "blendshapes": bs})

    return keyframes, duration_ms
