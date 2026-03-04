"""
Analyze text emotion using Qwen API (OpenAI-compatible mode).
"""

import json
from openai import OpenAI

SYSTEM_PROMPT = """你是一个虚拟人表情分析助手。分析输入文本的情感，只返回JSON，不要其他文字：
{
  "emotion": "happy或sad或angry或surprised或neutral中的一个",
  "intensity": 0.0到1.0之间的浮点数
}"""

# Maps emotion labels to Live2D blendshape parameters
EMOTION_BLENDSHAPES = {
    "happy": {
        "mouthSmileLeft": 0.8,
        "mouthSmileRight": 0.8,
        "cheekSquintLeft": 0.4,
        "cheekSquintRight": 0.4,
        "eyeSquintLeft": 0.3,
        "eyeSquintRight": 0.3,
    },
    "sad": {
        "mouthFrownLeft": 0.7,
        "mouthFrownRight": 0.7,
        "browInnerUp": 0.6,
        "eyeSquintLeft": 0.2,
        "eyeSquintRight": 0.2,
    },
    "angry": {
        "browDownLeft": 0.8,
        "browDownRight": 0.8,
        "noseSneerLeft": 0.3,
        "noseSneerRight": 0.3,
        "mouthFrownLeft": 0.4,
        "mouthFrownRight": 0.4,
    },
    "surprised": {
        "eyeWideLeft": 0.8,
        "eyeWideRight": 0.8,
        "browOuterUpLeft": 0.7,
        "browOuterUpRight": 0.7,
        "mouthFunnel": 0.3,
    },
    "neutral": {},
}


class TextAnalyzer:
    def __init__(self, api_key: str, model: str = "qwen-turbo",
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def analyze(self, text: str) -> dict:
        """
        Analyze text and return:
          {emotion, intensity, blendshapes}
        Falls back to neutral on any error.
        """
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                max_tokens=100,
            )
            result = json.loads(resp.choices[0].message.content)
        except Exception as e:
            print(f"[TextAnalyzer] Qwen error: {e}")
            result = {"emotion": "neutral", "intensity": 0.5}

        emotion = result.get("emotion", "neutral")
        if emotion not in EMOTION_BLENDSHAPES:
            emotion = "neutral"
        intensity = max(0.0, min(1.0, float(result.get("intensity", 0.5))))

        base = EMOTION_BLENDSHAPES.get(emotion, {})
        blendshapes = {k: round(v * intensity, 4) for k, v in base.items()}

        return {
            "emotion": emotion,
            "intensity": intensity,
            "blendshapes": blendshapes,
        }
