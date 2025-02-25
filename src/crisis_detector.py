# src/crisis_detector.py
"""
Crisis detection with a simple keyword approach for strong suicidal or self-harm ideation.
"""

SUICIDE_KEYWORDS = [
    "kill myself", "suicide", "end my life", "die by my own hand",
    "hurt myself", "self-harm", "overdose", "take my life"
]

async def crisis_detect(text: str) -> bool:
    text_lower = text.lower()
    for phrase in SUICIDE_KEYWORDS:
        if phrase in text_lower:
            return True
    return False
