"""Tests for src.configuration.config module."""

from __future__ import annotations

from pathlib import Path
from fastapi.background import P
import yaml
import pytest

from src.configuration.interface import ConfigLike
from src.configuration.config import Config, ConfigFactory, is_config_path, is_path_to_existing_file


def test_is_config_path_validation(tmp_path) -> None:
    """Validate config path detection and missing file handling."""
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text("root: 1\n", encoding="utf-8")

    assert is_config_path(str(cfg_file)) is True
    assert is_config_path(str(tmp_path / "config.txt"), raise_if_missing=False) is False
    with pytest.raises(FileNotFoundError):
        is_config_path(str(tmp_path / "missing.yml"))


def test_is_path_to_existing_file(tmp_path) -> None:
    """Validate helper checks for file presence."""
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text("root: 1\n", encoding="utf-8")

    assert is_path_to_existing_file(str(cfg_file)) is True
    assert is_path_to_existing_file(str(tmp_path / "absent.yml")) is False
    assert is_path_to_existing_file(123) is False


def test_config_get_defaults_and_mandatory() -> None:
    """Config.get should support defaults, callables, and mandatory flag."""
    cfg = Config(data={"section": {"value": 1}})

    assert cfg.get("section:value") == 1
    assert cfg.get("section:missing", default=lambda: 5) == 5

    class Sample:
        pass

    assert isinstance(cfg.get("section:another", default=Sample), Sample)
    with pytest.raises(ValueError):
        cfg.get("other", mandatory=True)


def test_config_update_and_exists() -> None:
    """Config.update should allow dotted paths and exists should reflect updates."""
    cfg = Config(data={"section": {"value": 1}})

    cfg.update({"section:new": 2})
    cfg.update([("other:path", 3)])

    assert cfg.exists("section:new") is True
    assert cfg.get("section:new") == 2
    assert cfg.get("other:path") == 3


def test_config_save_creates_backup_and_applies_updates(tmp_path: Path) -> None:
    """Saving creates a backup and writes provided updates."""
    cfg_file: Path = tmp_path / "config.yml"
    cfg_file.write_text("root:\n  value: 1\n", encoding="utf-8")

    cfg = Config(data={"root": {"value": 1}}, filename=str(cfg_file))
    cfg.save({"root:new": 2})

    loaded: dict = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    assert loaded["root"]["new"] == 2

    backups: list[Path] = list(tmp_path.glob("config.backup.*.yml"))
    assert len(backups) == 1


def test_configfactory_resolves_include_and_load(tmp_path: Path) -> None:
    """ConfigFactory resolves @include and @load directives using base path."""
    sub_file: Path = tmp_path / "sub.yml"
    sub_file.write_text("child:\n  key: sub\n", encoding="utf-8")

    csv_file: Path = tmp_path / "values.csv"
    csv_file.write_text("name,age\nalice,30\nbob,40\n", encoding="utf-8")

    main_file: Path = tmp_path / "config.yml"
    main_file.write_text(
        f"nested: \"@include:{sub_file.name}\"\nvalues: \"@load:{csv_file.name}\"\n",
        encoding="utf-8",
    )

    cfg: Config | ConfigLike = ConfigFactory().load(source=str(main_file), context="test_ctx")

    assert cfg.data["nested"]["child"]["key"] == "sub"
    assert cfg.data["values"] == [{"name": "alice", "age": "30"}, {"name": "bob", "age": "40"}]
