"""Tests for persistent highscores."""

import json
from pathlib import Path

from highscore import HighscoreStore


def test_missing_file_starts_empty(tmp_path: Path) -> None:
    """A missing highscore file is treated as an empty table."""
    store = HighscoreStore(str(tmp_path / "scores.json"))

    assert store.entries == []


def test_add_sorts_and_persists_scores(tmp_path: Path) -> None:
    """Adding scores keeps the highest values first and writes JSON."""
    path = tmp_path / "scores.json"
    store = HighscoreStore(str(path))

    store.add("bob", 10)
    store.add("alice", 50)

    assert [entry.name for entry in store.entries] == ["ALICE", "BOB"]
    assert [entry.score for entry in store.entries] == [50, 10]
    assert json.loads(path.read_text(encoding="utf-8")) == [
        {"name": "ALICE", "score": 50},
        {"name": "BOB", "score": 10},
    ]


def test_table_keeps_top_ten(tmp_path: Path) -> None:
    """Only the ten best scores are retained."""
    store = HighscoreStore(str(tmp_path / "scores.json"))

    for score in range(12):
        store.add("P", score)

    assert len(store.entries) == 10
    assert store.entries[0].score == 11
    assert store.entries[-1].score == 2


def test_name_is_cleaned(tmp_path: Path) -> None:
    """Names are uppercased, filtered and capped to ten chars."""
    store = HighscoreStore(str(tmp_path / "scores.json"))

    store.add("quentin!!!xxx", 42)

    assert store.entries[0].name == "QUENTINXXX"
