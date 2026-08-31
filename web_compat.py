"""Small runtime shims for packages unavailable in WebAssembly."""

from collections.abc import Callable, Mapping
import copy
from types import ModuleType
import sys
from typing import Optional, TypeVar, cast


_MISSING = object()
_DecoratorTarget = TypeVar("_DecoratorTarget")
_Model = TypeVar("_Model", bound="BaseModel")


class ValidationError(ValueError):
    """Match the exception imported by the configuration manager."""


class _FieldInfo:
    """Store only the default information required by the game."""

    def __init__(
        self,
        default: object = _MISSING,
        default_factory: Optional[Callable[[], object]] = None,
    ) -> None:
        self.default = default
        self.default_factory = default_factory


def Field(
    default: object = _MISSING,
    *,
    default_factory: Optional[Callable[[], object]] = None,
    **_: object,
) -> _FieldInfo:
    """Return the subset of Pydantic field metadata used at startup."""
    return _FieldInfo(default, default_factory)


def ConfigDict(**values: object) -> dict[str, object]:
    """Keep Pydantic model configuration declarations importable."""
    return dict(values)


def field_validator(
    *_: str,
    **__: object,
) -> Callable[[_DecoratorTarget], _DecoratorTarget]:
    """Preserve field validator declarations for trusted bundled data."""

    def decorator(target: _DecoratorTarget) -> _DecoratorTarget:
        return target

    return decorator


def model_validator(
    **_: object,
) -> Callable[[_DecoratorTarget], _DecoratorTarget]:
    """Preserve model validator declarations for trusted bundled data."""

    def decorator(target: _DecoratorTarget) -> _DecoratorTarget:
        return target

    return decorator


class BaseModel:
    """Construct the two trusted configuration models used by the game."""

    def __init_subclass__(cls, **_: object) -> None:
        """Accept Pydantic class options such as ``frozen=True``."""
        super().__init_subclass__()

    def __init__(self, **values: object) -> None:
        """Populate annotated fields from values or declared defaults."""
        model_type = type(self)
        annotations = cast(
            Mapping[str, object],
            model_type.__dict__.get("__annotations__", {}),
        )

        for name in annotations:
            declared = cast(object, getattr(model_type, name, _MISSING))
            if name in values:
                value = values[name]
            elif isinstance(declared, _FieldInfo):
                if declared.default_factory is not None:
                    value = declared.default_factory()
                elif declared.default is not _MISSING:
                    value = copy.deepcopy(declared.default)
                else:
                    raise ValidationError(f"Missing field: {name}")
            elif declared is not _MISSING:
                value = copy.deepcopy(declared)
            else:
                raise ValidationError(f"Missing field: {name}")

            if model_type.__name__ == "GameConfig" and name == "level":
                value = self._build_levels(model_type, value)
            setattr(self, name, value)

    @staticmethod
    def _build_levels(
        model_type: type[object],
        value: object,
    ) -> list[object]:
        """Convert bundled level dictionaries into LevelConfig objects."""
        if not isinstance(value, list):
            raise ValidationError("level must be a list")
        module = sys.modules[model_type.__module__]
        level_type = cast(type[BaseModel], getattr(module, "LevelConfig"))
        levels: list[object] = []
        for item in value:
            if isinstance(item, Mapping):
                levels.append(level_type.model_validate(item))
            else:
                levels.append(item)
        return levels

    @classmethod
    def model_validate(
        cls: type[_Model],
        values: Mapping[str, object],
    ) -> _Model:
        """Build a model from the mapping API used by the application."""
        return cls(**dict(values))


def install() -> None:
    """Expose the minimal modules required by the trusted web bundle."""
    pydantic = ModuleType("pydantic")
    for name, value in {
        "BaseModel": BaseModel,
        "ConfigDict": ConfigDict,
        "Field": Field,
        "ValidationError": ValidationError,
        "field_validator": field_validator,
        "model_validator": model_validator,
    }.items():
        setattr(pydantic, name, value)
    sys.modules["pydantic"] = pydantic

    typing_extensions = ModuleType("typing_extensions")
    typing_module = __import__("typing")
    setattr(typing_extensions, "Self", getattr(typing_module, "Self"))
    sys.modules["typing_extensions"] = typing_extensions
