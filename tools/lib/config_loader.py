"""Configuration helpers for the chat CLI."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised when PyYAML missing
    yaml = None

CHAT_DIR = Path(__file__).resolve().parents[1] / ".chat"
DEFAULT_CONFIG_PATH = CHAT_DIR / "config.yaml"


class ConfigError(RuntimeError):
    """Raised when the CLI configuration is missing or invalid."""


@dataclass
class SessionConfig:
    """Strongly typed configuration for a chat session."""

    model: str
    window_size: int
    should_truncate_results: bool

    @classmethod
    def from_mapping(cls, payload: Dict[str, Any]) -> "SessionConfig":
        try:
            model = str(payload["model"])
            window_size = int(payload["window_size"])
            should_truncate = bool(payload["should_truncate_results"])
        except KeyError as exc:
            raise ConfigError(f"Missing required config key: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise ConfigError("Invalid value in config.yaml") from exc
        return cls(model=model, window_size=window_size, should_truncate_results=should_truncate)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "window_size": self.window_size,
            "should_truncate_results": self.should_truncate_results,
        }

    def apply_overrides(
        self,
        *,
        model: Optional[str] = None,
        window_size: Optional[int] = None,
        should_truncate_results: Optional[bool] = None,
    ) -> "SessionConfig":
        return SessionConfig(
            model=model or self.model,
            window_size=window_size if window_size is not None else self.window_size,
            should_truncate_results=(
                should_truncate_results if should_truncate_results is not None else self.should_truncate_results
            ),
        )


def load_base_config(config_path: Optional[Path] = None) -> SessionConfig:
    """Load and validate the default configuration file."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        raise ConfigError(
            textwrap.dedent(
                f"""
                Missing required config file: {path}
                Create the file using the template committed under server/tools/.chat/config.yaml.
                """
            ).strip()
        )
    with path.open("r", encoding="utf-8") as handle:
        raw_text = handle.read()
        if yaml is not None:
            data = yaml.safe_load(raw_text) or {}
        else:  # pragma: no cover - executed when PyYAML unavailable
            data = _simple_yaml_parse(raw_text)
    if not isinstance(data, dict):
        raise ConfigError("config.yaml must contain a mapping/object at the top level")
    return SessionConfig.from_mapping(data)


def session_config_from_metadata(metadata: Dict[str, Any]) -> Optional[SessionConfig]:
    """Build a SessionConfig from stored metadata."""
    config_block = metadata.get("config")
    if not config_block:
        return None
    if isinstance(config_block, SessionConfig):
        return config_block
    if not isinstance(config_block, dict):
        raise ConfigError("metadata 'config' block must be a mapping")
    return SessionConfig.from_mapping(config_block)


def _simple_yaml_parse(text: str) -> Dict[str, Any]:
    """Very small YAML subset parser used when PyYAML is unavailable."""

    def _coerce(value: str) -> Any:
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        try:
            return int(value)
        except ValueError:
            return value

    data: Dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ConfigError("Unable to parse config.yaml; install PyYAML for complex files.")
        key, value = stripped.split(":", 1)
        data[key.strip()] = _coerce(value.strip())
    return data


