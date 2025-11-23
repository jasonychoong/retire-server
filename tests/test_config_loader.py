"""Config loader unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from server.tools.lib.config_loader import (
    ConfigError,
    SessionConfig,
    load_base_config,
    session_config_from_metadata,
)


def test_load_base_config_success(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("model: gpt-5.1\nwindow_size: 16\nshould_truncate_results: false\n", encoding="utf-8")

    cfg = load_base_config(config_path=config_path)

    assert cfg.model == "gpt-5.1"
    assert cfg.window_size == 16
    assert cfg.should_truncate_results is False


def test_load_base_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_base_config(config_path=tmp_path / "missing.yaml")


def test_session_config_overrides_and_metadata_round_trip() -> None:
    cfg = SessionConfig(model="base", window_size=20, should_truncate_results=True)
    updated = cfg.apply_overrides(model="alt", window_size=5, should_truncate_results=False)

    assert updated.model == "alt"
    assert updated.window_size == 5
    assert updated.should_truncate_results is False

    metadata_cfg = session_config_from_metadata({"config": updated.to_dict()})
    assert metadata_cfg == updated

