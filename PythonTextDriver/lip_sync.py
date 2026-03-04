"""
Lip sync module: maps ISI TTS phonemes to Live2D mouth blendshape keyframes.

ISI phoneme format: "initial_final" e.g. "j_in", "w_an", "zh_ong"
or bare syllables like "a", "o" for vowel-only sounds.
"""


# Vowel detection: check each candidate in priority order (first match wins).
# The check is for substrings in the phoneme's final (after underscore).
_VOWEL_CHECKS = [
    ("a", "a"),   # a, ai, ao, an, ang, ia, ua, iao, ian, iang, …
    ("o", "o"),   # o, ou, ong, uo
    ("e", "e"),   # e, ei, en, eng, ie, ue, er
    ("i", "i"),   # i, in, ing, ia, ie, iu, ian, iang
    ("u", "u"),   # u, ui, un, uo, ua, uan
    ("v", "v"),   # v (ü), ve, van, vn
]

# Viseme targets keyed by dominant vowel.
# jawOpen, mouthFunnel, mouthPucker — the three primary lip-sync channels.
_VISEME_TABLE = {
    "a": {"jawOpen": 0.80, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "o": {"jawOpen": 0.50, "mouthFunnel": 0.70, "mouthPucker": 0.00},
    "e": {"jawOpen": 0.45, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "i": {"jawOpen": 0.20, "mouthFunnel": 0.00, "mouthPucker": 0.00},
    "u": {"jawOpen": 0.35, "mouthFunnel": 0.75, "mouthPucker": 0.30},
    "v": {"jawOpen": 0.15, "mouthFunnel": 0.20, "mouthPucker": 0.80},
    "":  {"jawOpen": 0.05, "mouthFunnel": 0.00, "mouthPucker": 0.00},  # consonant/closed
}

_CLOSED = _VISEME_TABLE[""]


def extract_dominant_vowel(phoneme: str) -> str:
    """
    Extract the dominant vowel from an ISI phoneme string.

    ISI phonemes look like "j_in" (initial_final) or bare strings like "a".
    We examine the final (韵母) portion for the most distinctive vowel.

    Returns one of: "a", "o", "e", "i", "u", "v", or "" (consonant/silence).
    """
    parts = phoneme.split("_", 1)
    final = parts[-1].lower()          # use the final part (韵母)
    for vowel_char, vowel_key in _VOWEL_CHECKS:
        if vowel_char in final:
            return vowel_key
    return ""


def viseme_for_vowel(vowel: str) -> dict:
    """Return mouth blendshape values for a given dominant vowel."""
    return dict(_VISEME_TABLE.get(vowel, _CLOSED))


def phonemes_to_keyframes(phoneme_flat: list) -> list:
    """
    Convert ISI phoneme_flat list to animation keyframes.

    Each input item has: char, phoneme, tone, begin_ms, end_ms.
    Each output keyframe: { "time_ms": int, "blendshapes": dict }.

    Strategy:
      - At begin_ms: target viseme for this phoneme
      - At end_ms (when there is a gap to the next phoneme > 30 ms): insert
        a closing frame so the mouth returns to neutral between words.
    """
    if not phoneme_flat:
        return []

    keyframes = []

    for i, ph in enumerate(phoneme_flat):
        phoneme_str = ph.get("phoneme", "")
        begin_ms    = ph.get("begin_ms", 0)
        end_ms      = ph.get("end_ms", begin_ms)

        vowel = extract_dominant_vowel(phoneme_str)
        bs    = viseme_for_vowel(vowel)

        keyframes.append({"time_ms": begin_ms, "blendshapes": dict(bs)})

        # Insert closing frame when there is a visible gap to the next phoneme,
        # or unconditionally after the very last phoneme.
        is_last    = (i == len(phoneme_flat) - 1)
        next_begin = phoneme_flat[i + 1]["begin_ms"] if not is_last else end_ms
        if is_last or (next_begin > end_ms and (next_begin - end_ms) > 30):
            keyframes.append({"time_ms": end_ms, "blendshapes": dict(_CLOSED)})

    return sorted(keyframes, key=lambda k: k["time_ms"])
