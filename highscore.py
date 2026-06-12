"""Persistent top-10 highscore table."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HighscoreEntry:
    """One stored highscore row."""

    name: str
    score: int


class HighscoreStore:
    """Load, update and save the highscore table."""

    MAX_ENTRIES = 10
    MAX_NAME_LENGTH = 10
    DEFAULT_NAME = "PLAYER"

    def __init__(self, filename: str) -> None:
        """Load highscores from ``filename`` if possible."""
        self.path = Path(filename)
        self.entries: list[HighscoreEntry] = self._load()

    def qualifies(self, score: int) -> bool:
        """Return True if ``score`` should enter the table."""
        if len(self.entries) < self.MAX_ENTRIES:
            return True
        if score > self.entries[-1].score:
            return True
        return False

    def add(self, name: str, score: int) -> None:
        """Add a score, sort the table and persist it."""
        self.entries.append(
            HighscoreEntry(self._clean_name(name), max(0, score))
        )
        self.entries.sort(key=lambda entry: entry.score, reverse=True)
        self.entries = self.entries[:self.MAX_ENTRIES]
        self._save()

    def _load(self) -> list[HighscoreEntry]:
        """Read valid entries from disk, ignoring broken files."""
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

        if not isinstance(raw, list):
            return []

        entries = []
        for item in raw:
            entry = self._entry_from_raw(item)
            if entry is not None:
                entries.append(entry)
        entries.sort(key=lambda entry: entry.score, reverse=True)
        return entries[:self.MAX_ENTRIES]

    def _save(self) -> None:
        """Write the current table to disk."""
        data = [
            {"name": entry.name, "score": entry.score}
            for entry in self.entries
        ]
        try:
            self.path.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8",
            )
        except OSError:
            return

    def _entry_from_raw(self, item: Any) -> HighscoreEntry | None:
        """Convert one JSON item into a valid entry when possible."""
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        score = item.get("score")
        if not isinstance(name, str) or not isinstance(score, int):
            return None
        return HighscoreEntry(self._clean_name(name), max(0, score))

    def _clean_name(self, name: str) -> str:
        """Keep only alphanumeric chars and spaces, capped to 10 chars."""
        cleaned = []

        for raw_char in name:
            if raw_char.isalnum() or raw_char == " ":
                cleaned.append(raw_char.upper())

        if not cleaned:
            return self.DEFAULT_NAME

        return "".join(cleaned[:self.MAX_NAME_LENGTH])
