import json
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "detection_rules.json"


@lru_cache(maxsize=1)
def load_detection_rules():
    """Load detection rules from the JSON file once and cache them."""
    with RULES_PATH.open("r", encoding="utf-8") as rules_file:
        return json.load(rules_file)
