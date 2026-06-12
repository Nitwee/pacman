"""Pydantic models used to validate the game configuration."""

from pydantic import Field, BaseModel, ConfigDict, field_validator


class LevelConfig(BaseModel):
    """Configuration for a single generated maze level."""

    width: int = Field(default=15, ge=10, le=30)
    height: int = Field(default=15, ge=10, le=30)

    model_config = ConfigDict(extra="ignore")


class GameConfig(BaseModel):
    """Validated configuration used by the Pac-Man application."""

    highscore_filename: str = Field(default="highscore.json", min_length=6)
    lives: int = Field(default=3, ge=1)
    pacgum: int = Field(default=42, ge=0)
    points_per_pacgum: int = Field(default=10, ge=1)
    points_per_super_pacgum: int = Field(default=50, ge=0)
    points_per_ghost: int = Field(default=200, ge=0)
    seed: int = Field(default=42, ge=0)
    level_max_time: int = Field(default=90, ge=1)

    @field_validator("highscore_filename")
    @classmethod
    def validate_highscore_filename(cls, value: str) -> str:
        """Validate and normalize the highscore JSON filename.

        Args:
            value: Filename loaded from the raw configuration.

        Returns:
            Filename without surrounding whitespace.

        Raises:
            ValueError: If the filename does not end with ``.json``.
        """
        cleaned = value.strip()
        if not cleaned.lower().endswith(".json"):
            raise ValueError("highscore_filename must end with .json")
        return cleaned

    @staticmethod
    def default_levels() -> list[LevelConfig]:
        """Return the default list of level configurations.

        Returns:
            Ten default maze levels.
        """
        return [
            LevelConfig(width=15, height=15),
            LevelConfig(width=15, height=15),
            LevelConfig(width=15, height=15),
            LevelConfig(width=15, height=15),
            LevelConfig(width=15, height=15),
            LevelConfig(width=15, height=15),
            LevelConfig(width=15, height=15),
            LevelConfig(width=15, height=15),
            LevelConfig(width=15, height=15),
            LevelConfig(width=15, height=15),
        ]

    level: list[LevelConfig] = Field(
        default_factory=default_levels,
        min_length=10,
    )
    model_config = ConfigDict(extra="ignore")
