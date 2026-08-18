"""Unit tests for the Postgres document matcher (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from db import match, project, sort_docs  # noqa: E402


def test_eq_and_or_exists():
    doc = {"id": "REQ-1045", "requesterId": "USR-STU", "anonymous": True}
    assert match(doc, {"id": "REQ-1045"})
    assert not match(doc, {"id": "REQ-1"})
    assert match(doc, {"id": {"$in": ["REQ-1045", "REQ-1042"]}})
    assert match(doc, {"$or": [{"requesterId": None}, {"requesterId": {"$exists": False}}]}) is False
    assert match({"id": "x"}, {"requesterId": {"$exists": False}})
    assert match({"id": "x", "requesterId": None}, {"$or": [{"requesterId": None}, {"requesterId": {"$exists": False}}]})


def test_regex_and_range():
    lab = {"name": "Physics Lab 3", "startHour": 21, "endHour": 23, "status": "CONFIRMED"}
    assert match(lab, {"name": {"$regex": "physics lab 3", "$options": "i"}})
    assert match(lab, {"startHour": {"$lt": 22}, "endHour": {"$gt": 20}, "status": {"$ne": "CANCELLED"}})
    assert not match(lab, {"status": {"$ne": "CONFIRMED"}})


def test_project_and_sort():
    docs = [{"id": "a", "seq": 2, "hash": "h2", "extra": 1}, {"id": "b", "seq": 1, "hash": "h1"}]
    assert [d["id"] for d in sort_docs(docs, [("seq", -1)])] == ["a", "b"]
    assert project(docs[0], {"_id": 0, "hash": 1}) == {"hash": "h2"}
    assert "pendingArgs" not in project({"id": "a", "pendingArgs": {"x": 1}}, {"_id": 0, "pendingArgs": 0})


if __name__ == "__main__":
    test_eq_and_or_exists()
    test_regex_and_range()
    test_project_and_sort()
    print("ok")
