from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.target_model import compare_target_models


def test_main_loads_the_two_models_and_reports_their_metadata(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    original_path = tmp_path / "original.yml"
    extended_path = tmp_path / "extended.yml"
    original_path.touch()
    extended_path.touch()

    original_model = SimpleNamespace(
        model=SimpleNamespace(name="Baseline", version="2.0.0"),
        entities={"site": object()},
    )
    extended_model = SimpleNamespace(
        model=SimpleNamespace(name="Expanded", version="2.1.0"),
        entities={"site": object()},
    )
    project = SimpleNamespace(entities={"site": object()})
    loaded_paths: list[Path] = []
    model_by_path = {
        original_path: original_model,
        extended_path: extended_model,
    }

    def load_target_model(path: Path) -> SimpleNamespace:
        loaded_paths.append(path)
        return model_by_path[path]

    monkeypatch.setattr(compare_target_models, "load_target_model", load_target_model)
    monkeypatch.setattr(compare_target_models, "load_project", lambda _: project)
    validation_results = iter(
        (
            {"total_errors": 1, "entity_count": 1, "entity_errors": {"site": [{"message": "baseline issue"}]}},
            {"total_errors": 0, "entity_count": 0, "entity_errors": {}},
        )
    )
    monkeypatch.setattr(compare_target_models, "validate_project", lambda *_: next(validation_results))

    result = compare_target_models.main(
        [
            "--original-model",
            str(original_path),
            "--extended-model",
            str(extended_path),
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert loaded_paths == [original_path, extended_path]
    assert "ORIGINAL MODEL (Baseline v2.0.0)" in output
    assert "EXTENDED MODEL (Expanded v2.1.0)" in output


def test_main_rejects_the_same_model_file_for_both_inputs(tmp_path: Path) -> None:
    model_path = tmp_path / "model.yml"
    model_path.touch()

    with pytest.raises(SystemExit) as exc_info:
        compare_target_models.main(
            [
                "--original-model",
                str(model_path),
                "--extended-model",
                str(model_path),
            ]
        )

    assert exc_info.value.code == 2
