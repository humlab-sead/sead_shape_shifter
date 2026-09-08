"""Tests for src.configuration.config module."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.configuration import Config, ConfigLike, is_path_to_existing_file, is_yaml_file, load_config, resolve_directives


def test_is_config_path_validation(tmp_path) -> None:
    """Validate config path detection and missing file handling."""
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text("root: 1\n", encoding="utf-8")

    assert is_yaml_file(str(cfg_file)) is True
    assert is_yaml_file(str(tmp_path / "config.txt"), raise_if_missing=False) is False
    with pytest.raises(FileNotFoundError):
        is_yaml_file(str(tmp_path / "missing.yml"))


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


def test_config_resolve_applies_env(monkeypatch) -> None:
    """Config.resolve should apply env var replacement and prefix injection."""
    monkeypatch.setenv("API_URL", "https://example.test")
    monkeypatch.setenv("APP_SETTINGS_TOKEN", "secret")

    cfg = Config(data={"settings": {"url": "${API_URL}"}}, env_prefix="APP")
    resolved = cfg.resolve()

    assert resolved.data["settings"]["url"] == "https://example.test"
    assert resolved.data["settings"]["token"] == "secret"
    assert resolved is cfg


def test_configfactory_resolves_include_and_load(tmp_path: Path, monkeypatch) -> None:
    """load_config resolves @include and @load directives using base path."""
    sub_file: Path = tmp_path / "sub.yml"
    sub_file.write_text("child:\n  key: sub\n", encoding="utf-8")

    csv_file: Path = tmp_path / "values.csv"
    csv_file.write_text("name,age\nalice,30\nbob,40\n", encoding="utf-8")

    main_file: Path = tmp_path / "config.yml"
    main_file.write_text(
        f'nested: "@include:{sub_file.name}"\nvalues: "@load:{csv_file.name}"\napi: "${{API_URL}}"\n',
        encoding="utf-8",
    )

    monkeypatch.setenv("API_URL", "https://example.test")
    cfg: Config | ConfigLike = load_config(source=str(main_file), context="test_ctx")

    assert cfg.data["nested"]["child"]["key"] == "sub"
    assert cfg.data["values"] == [{"name": "alice", "age": "30"}, {"name": "bob", "age": "40"}]
    assert cfg.data["api"] == "https://example.test"


def test_configfactory_preserves_empty_load_result(tmp_path: Path) -> None:
    """load_config should keep an empty loaded file instead of the directive string."""
    empty_csv: Path = tmp_path / "empty.csv"
    empty_csv.write_text("name,age\n", encoding="utf-8")

    main_file: Path = tmp_path / "config.yml"
    main_file.write_text(f'values: "@load:{empty_csv.name}"\n', encoding="utf-8")

    cfg: Config | ConfigLike = load_config(source=str(main_file), context="test_ctx")

    assert cfg.data["values"] == []


def test_configfactory_loads_from_dotpath_filename(tmp_path: Path) -> None:
    """load_config should dereference dotpaths that point to a filename string."""
    csv_file: Path = tmp_path / "values.csv"
    csv_file.write_text("name,age\nalice,30\n", encoding="utf-8")

    main_file: Path = tmp_path / "config.yml"
    main_file.write_text(
        'sources:\n  translation_file: "values.csv"\nvalues: "@load:sources.translation_file"\n',
        encoding="utf-8",
    )

    cfg: Config | ConfigLike = load_config(source=str(main_file), context="test_ctx")

    assert cfg.data["values"] == [{"name": "alice", "age": "30"}]


def test_resolve_references_uses_any_existing_source_file_for_relative_paths(tmp_path: Path) -> None:
    """resolve_references should resolve relative includes from non-YAML source files too."""
    child_file: Path = tmp_path / "child.yml"
    child_file.write_text("child:\n  key: value\n", encoding="utf-8")

    source_file: Path = tmp_path / "config.json"
    source_file.write_text('{"nested": "@include:child.yml"}', encoding="utf-8")

    resolved = resolve_directives({"nested": "@include:child.yml"}, source_path=str(source_file))

    assert resolved["nested"]["child"]["key"] == "value"


def test_resolve_directives_rejects_paths_outside_approved_roots(tmp_path: Path) -> None:
    """Directive files must remain beneath the supplied project or shared roots."""
    project_root = tmp_path / "projects" / "demo"
    project_root.mkdir(parents=True)
    source_file = project_root / "shapeshifter.yml"
    outside_file = tmp_path / "outside.yml"
    outside_file.write_text("value: escaped\n", encoding="utf-8")

    with pytest.raises(ValueError, match="approved data roots"):
        resolve_directives(
            {"nested": "@include: ../outside.yml"},
            source_path=str(source_file),
            allowed_roots=(project_root,),
        )


def test_resolve_directives_allows_load_from_approved_shared_root(tmp_path: Path) -> None:
    """@load may read a file from an explicitly approved shared root."""
    project_root = tmp_path / "projects" / "demo"
    shared_root = tmp_path / "shared"
    project_root.mkdir(parents=True)
    shared_root.mkdir()
    source_file = project_root / "shapeshifter.yml"
    values_file = shared_root / "values.csv"
    values_file.write_text("name\nalice\n", encoding="utf-8")

    resolved = resolve_directives(
        {"values": f"@load: {values_file}"},
        source_path=str(source_file),
        allowed_roots=(project_root, shared_root),
    )

    assert resolved["values"] == [{"name": "alice"}]


def test_resolve_directives_rejects_absolute_and_symlink_escape(tmp_path: Path) -> None:
    """Directive paths cannot bypass roots with absolute names or symlinks."""
    project_root = tmp_path / "projects" / "demo"
    project_root.mkdir(parents=True)
    source_file = project_root / "shapeshifter.yml"
    outside_file = tmp_path / "outside.yml"
    outside_file.write_text("value: escaped\n", encoding="utf-8")
    symlink = project_root / "linked.yml"
    symlink.symlink_to(outside_file)

    for directive in (f"@include: {outside_file}", "@include: linked.yml"):
        with pytest.raises(ValueError, match="approved data roots"):
            resolve_directives(
                {"nested": directive},
                source_path=str(source_file),
                allowed_roots=(project_root,),
            )


def test_resolve_directives_rejects_cross_project_include(tmp_path: Path) -> None:
    """A project cannot include a file from a sibling project root."""
    project_root = tmp_path / "projects" / "project-a"
    other_project = tmp_path / "projects" / "project-b"
    project_root.mkdir(parents=True)
    other_project.mkdir()
    source_file = project_root / "shapeshifter.yml"
    (other_project / "shared.yml").write_text("value: other-project\n", encoding="utf-8")

    with pytest.raises(ValueError, match="approved data roots"):
        resolve_directives(
            {"nested": "@include: ../project-b/shared.yml"},
            source_path=str(source_file),
            allowed_roots=(project_root,),
        )


def test_configfactory_applies_env_prefix(tmp_path: Path, monkeypatch) -> None:
    """load_config should inject env-prefixed values into loaded data."""
    monkeypatch.setenv("MYAPP_SECTION_KEY", "from_env")

    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text("section:\n  placeholder: 1\n", encoding="utf-8")

    cfg: Config = load_config(source=str(cfg_file), env_prefix="MYAPP")  # type: ignore[assignment]

    assert cfg.data["section"]["key"] == "from_env"
    assert cfg.env_prefix == "MYAPP"
