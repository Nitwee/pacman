"""Read and decode the JSON configuration file."""

import sys
import json
from pathlib import Path
from typing import Any


class ParserError(Exception):
    """Error raised when the configuration file cannot be parsed."""

    pass


class Parser:
    """Load a JSON configuration file into a raw dictionary."""

    def __init__(self, filename: str) -> None:
        """Initialize the parser and load the configuration file.

        Args:
            filename: Path to the JSON configuration file.
        """
        self.content = ""
        self.raw_config: dict[str, Any] = {}
        self.load_file(filename)

    def load_file(self, filename: str) -> None:
        """Read the file, remove comments and parse the JSON content.

        Args:
            filename: Path to the JSON configuration file.
        """
        try:
            raw_content = self.open_file(filename)
            content = self.remove_comments(raw_content)
            self.raw_config = self.parse_json(content)
        except ParserError as e:
            print(f"Cannot read config: {e}", file=sys.stderr)
            print("Fallback to default config.", file=sys.stderr)
            self.raw_config = {}

    def parse_json(self, content: str) -> dict[str, Any]:
        """Convert a JSON string into a dictionary.

        Args:
            content: JSON content without comment lines.

        Returns:
            Parsed configuration data.

        Raises:
            ParserError: If the JSON is invalid or is not an object.
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ParserError(f"Invalid JSON: {e}")
        if not isinstance(data, dict):
            raise ParserError("Config must be a JSON object")
        return data

    def remove_comments(self, content: str) -> str:
        """Remove full-line comments from the configuration content.

        Args:
            content: Raw file content.

        Returns:
            Content rebuilt without lines starting with ``#`` after
            optional leading whitespace.
        """
        res = []
        for line in content.splitlines():
            if not line.lstrip().startswith("#"):
                res.append(line)
        return "\n".join(res)

    def open_file(self, filename: str) -> str:
        """Open and read a JSON configuration file.

        Args:
            filename: Path to the JSON configuration file.

        Returns:
            Raw file content.

        Raises:
            ParserError: If the path is invalid or cannot be read.
        """
        if not filename or filename.strip() == "":
            raise ParserError("Missing Filename")
        path = Path(filename)
        if not path.exists():
            raise ParserError(f"File {filename} does not exists")
        if not path.is_file():
            raise ParserError(f"{filename} must be a file.")
        if path.suffix != ".json":
            raise ParserError("File extension must be '.json'")
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise ParserError(f"Error reading file {filename}: {e}")
        return content
