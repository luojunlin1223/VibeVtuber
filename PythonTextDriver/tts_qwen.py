"""
Qwen TTS via DashScope SDK.
Returns audio URL + full metadata dict for debugging.
"""

import time
import dashscope

VOICES = [
    {"id": "Cherry",  "label": "Cherry  芊悦（女·温柔）"},
    {"id": "Serena",  "label": "Serena  苏瑶（女·知性）"},
    {"id": "Ethan",   "label": "Ethan   晨煦（男·稳重）"},
    {"id": "Chelsie", "label": "Chelsie 千雪（女·清爽）"},
    {"id": "Momo",    "label": "Momo    茉兔（女·活泼）"},
    {"id": "Vivian",  "label": "Vivian  十三（女·个性）"},
    {"id": "Moon",    "label": "Moon    月白（女·温暖）"},
    {"id": "Maia",    "label": "Maia    四月（女·甜美）"},
    {"id": "Kai",     "label": "Kai     凯  （男·阳光）"},
]

MODELS = [
    {"id": "qwen3-tts-flash", "label": "qwen3-tts-flash（最新·快速）"},
    {"id": "qwen-tts",        "label": "qwen-tts（稳定版）"},
]


def synthesize(text: str, voice: str = "Cherry",
               model: str = "qwen3-tts-flash", api_key: str = "") -> dict:
    """
    Call Qwen TTS and return a debug-friendly dict:
      ok, request, response (metadata), audio_url
    """
    t0 = time.time()
    request_info = {
        "model": model,
        "voice": voice,
        "text": text,
        "text_length": len(text),
        "language_type": "Chinese",
    }

    if not api_key:
        return {"ok": False, "error": "API Key 未配置", "request": request_info}

    try:
        dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
        resp = dashscope.MultiModalConversation.call(
            model=model,
            api_key=api_key,
            text=text,
            voice=voice,
            language_type="Chinese",
            stream=False,
        )
        elapsed = round(time.time() - t0, 3)

        if resp.status_code != 200:
            return {
                "ok": False,
                "error": f"API 返回 {resp.status_code}: {getattr(resp, 'message', '')}",
                "request": request_info,
                "elapsed_s": elapsed,
            }

        audio = resp.output.audio
        usage = resp.usage

        return {
            "ok": True,
            "request": request_info,
            "response": {
                "request_id":   resp.request_id,
                "status_code":  resp.status_code,
                "audio_id":     audio.id,
                "audio_url":    audio.url,
                "audio_format": "wav",
                "expires_at":   audio.expires_at,
                "usage": {
                    "input_tokens":  usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                },
                "elapsed_s": elapsed,
            },
            "audio_url": audio.url,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "request": request_info,
            "elapsed_s": round(time.time() - t0, 3),
        }
