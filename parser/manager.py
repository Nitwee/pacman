"""Coordinate file parsing and configuration validation."""

from parser.validator import GameConfig
from parser.parser import Parser
from pydantic import ValidationError
import sys


class ConfigManager:
    """Build a validated game configuration from a config file."""

    def __init__(self, filename: str) -> None:
        """Initialize the manager and expose the final game config.

        Args:
            filename: Path to the JSON configuration file.
        """
        parser = Parser(filename)
        clean_config: dict[str, object] = {}
        for key, value in parser.raw_config.items():
            try:
                valid = GameConfig.model_validate({key: value})
                clean_config[key] = getattr(valid, key)
            except ValidationError:
                print(
                    f"Invalid value for '{key}' ({value}), "
                    "using default instead",
                    file=sys.stderr,
                )
            except AttributeError:
                continue
        self.config: GameConfig = GameConfig.model_validate(clean_config)
