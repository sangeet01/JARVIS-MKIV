"""
JARVIS Training Data Collector
Appends high-quality interaction pairs to dataset.jsonl for fine-tuning.
"""
import json
import os
import time
import threading
from pathlib import Path

_DATASET_PATH = Path(__file__).parent / "dataset.jsonl"
_LOCK = threading.Lock()

_CATEGORY_KEYWORDS = {
    "identity": ["who are you", "what are you", "who made", "your name", "your purpose", "made you", "created you"],
    "system": ["launch", "open", "run", "execute", "start", "close", "kill", "process", "install", "screenshot", "terminal"],
    "calendar": ["calendar", "schedule", "meeting", "event", "appointment", "remind", "alarm", "today", "tomorrow", "week"],
    "weather": ["weather", "temperature", "forecast", "rain", "wind", "humidity", "sunny", "cloudy"],
    "memory": ["remember", "recall", "memory", "forget", "store", "retrieve", "note", "what did i"],
}


def _infer_category(prompt: str) -> str:
    prompt_lower = prompt.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in prompt_lower for kw in keywords):
            return category
    return "general"


def log_training_pair(prompt: str, response: str, category: str = "") -> bool:
    """
    Append a training pair to dataset.jsonl.
    Returns True if written, False if duplicate or skipped.
    Thread-safe.
    """
    if not category:
        category = _infer_category(prompt)

    with _LOCK:
        # Load existing prompts for deduplication
        existing_prompts = set()
        if _DATASET_PATH.exists():
            with open(_DATASET_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            existing_prompts.add(entry.get("instruction", ""))
                        except json.JSONDecodeError:
                            pass

        if prompt in existing_prompts:
            return False

        entry = {
            "instruction": prompt,
            "response": response,
            "category": category,
            "timestamp": int(time.time()),
        }

        with open(_DATASET_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return True
