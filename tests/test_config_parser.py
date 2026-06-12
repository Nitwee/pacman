"""Tests for configuration parsing and validation."""

from pathlib import Path

import pytest

from parser.manager import ConfigManager
from parser.parser import Parser
from parser.validator import GameConfig


def write_config(path: Path, content: str) -> Path:
    """Write a temporary configuration file.

    Args:
        path: Target file path.
        content: File content to write.

    Returns:
        The path passed as argument.
    """
    path.write_text(content, encoding="utf-8")
    return (path)


def test_config_manager_loads_valid_config(tmp_path: Path) -> None:
    """Load a complete valid configuration file."""
    config_path = write_config(
        tmp_path / "config.json",
        """
# Pac-Man config
{
  "highscore_filename": " scores.json ",
  "lives": 5,
  "points_per_pacgum": 20,
  "level": [
    {"width": 10, "height": 10},
    {"width": 11, "height": 10},
    {"width": 12, "height": 10},
    {"width": 13, "height": 10},
    {"width": 14, "height": 10},
    {"width": 15, "height": 10},
    {"width": 16, "height": 10},
    {"width": 17, "height": 10},
    {"width": 18, "height": 10},
    {"width": 19, "height": 10}
  ]
}
""",
    )

    config = ConfigManager(str(config_path)).config

    assert config.highscore_filename == "scores.json"
    assert config.lives == 5
    assert config.points_per_pacgum == 20
    assert len(config.level) == 10
    assert config.level[0].width == 10


def test_config_manager_falls_back_for_invalid_values(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Replace invalid provided values with model defaults."""
    config_path = write_config(
        tmp_path / "config.json",
        """
{
  "highscore_filename": "scores.txt",
  "lives": 0,
  "points_per_pacgum": 25,
  "level": [{"width": 10, "height": 10}]
}
""",
    )

    config = ConfigManager(str(config_path)).config
    captured = capsys.readouterr()

    assert config.highscore_filename == "highscore.json"
    assert config.lives == 3
    assert config.points_per_pacgum == 25
    assert len(config.level) == 10
    assert "Invalid value for 'highscore_filename'" in captured.err
    assert "Invalid value for 'lives'" in captured.err
    assert "Invalid value for 'level'" in captured.err


def test_config_manager_ignores_unknown_keys(tmp_path: Path) -> None:
    """Ignore keys that are not part of the public config schema."""
    config_path = write_config(
        tmp_path / "config.json",
        """
{
  "lives": 4,
  "unknown_key": true
}
""",
    )

    config = ConfigManager(str(config_path)).config

    assert config.lives == 4
    assert not hasattr(config, "unknown_key")


def test_config_manager_falls_back_when_file_is_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Use the default config when the file cannot be read."""
    config_path = tmp_path / "missing.json"

    config = ConfigManager(str(config_path)).config
    captured = capsys.readouterr()

    assert config == GameConfig()
    assert "Cannot read config" in captured.err


def test_config_manager_falls_back_on_invalid_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Use the default config when the file is not valid JSON."""
    config_path = write_config(tmp_path / "config.json", "{")

    config = ConfigManager(str(config_path)).config
    captured = capsys.readouterr()

    assert config == GameConfig()
    assert "Invalid JSON" in captured.err


def test_config_manager_falls_back_on_invalid_encoding(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Use the default config when the file is not valid UTF-8."""
    config_path = tmp_path / "config.json"
    config_path.write_bytes(b"\xff\xfe\x00")

    config = ConfigManager(str(config_path)).config
    captured = capsys.readouterr()

    assert config == GameConfig()
    assert "Cannot read config" in captured.err


def test_parser_removes_comment_lines(tmp_path: Path) -> None:
    """Drop lines that are full-line comments."""
    config_path = write_config(
        tmp_path / "config.json",
        """
# top-level comment
{
  # field comment
  "lives": 6
}
""",
    )

    parser = Parser(str(config_path))

    assert parser.raw_config == {"lives": 6}
