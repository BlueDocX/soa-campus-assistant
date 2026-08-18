"""Unit tests for the LLM JSON helper and auto-file gate (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from llm import extract_json  # noqa: E402
from orchestrator import detect_lang, should_autofile  # noqa: E402


def test_extract_json_raw_and_fenced():
    assert extract_json('{"intent": "maintenance"}')["intent"] == "maintenance"
    assert extract_json('Sure.\n```json\n{"conflict": true, "confidence": 0.8}\n```')["conflict"] is True


def test_detect_lang():
    assert detect_lang("I need a bonafide") == "en"
    assert detect_lang("मुझे बोनाफाइड प्रमाणपत्र चाहिए") == "hi"
    assert detect_lang("ମୋତେ ଲାବ୍ ବୁକ୍ କରିବାକୁ ହେବ") == "od"


def test_keyword_exam_week_flags():
    from orchestrator import _keyword_interpret
    lab = _keyword_interpret("Book Physics Lab 3 tonight at 9pm, it is exam week")
    assert lab["intent"] == "lab_booking"
    assert lab["after_hours"] and lab["exam_week"]


def test_should_autofile():
    assert should_autofile({"intent": "certificate", "confidence": 0.9}, True)
    assert not should_autofile({"intent": "certificate", "confidence": 0.9}, False)
    assert not should_autofile({"intent": "unknown", "confidence": 0.9}, True)
    assert not should_autofile({"intent": "maintenance", "confidence": 0.2}, True)


if __name__ == "__main__":
    test_extract_json_raw_and_fenced()
    test_detect_lang()
    test_should_autofile()
    print("ok")
