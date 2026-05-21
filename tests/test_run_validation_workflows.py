from scripts import run_validation_workflows as script


def test_main_runs_data_workflow_only(monkeypatch, tmp_path, capsys):
    project_file = tmp_path / "shapeshifter.yml"
    project_file.write_text("metadata: {}\nentities: {}\n", encoding="utf-8")

    calls: list[str] = []

    monkeypatch.setattr(script, "setup_logging", lambda **kwargs: None)
    monkeypatch.setattr(script, "load_project", lambda project_path, env_file: object())
    monkeypatch.setattr(
        script,
        "run_structural_validation",
        lambda project: (_ for _ in ()).throw(AssertionError("structural workflow should not run")),
    )
    monkeypatch.setattr(
        script,
        "run_conformance_validation",
        lambda project: (_ for _ in ()).throw(AssertionError("conformance workflow should not run")),
    )

    async def fake_run_data_validation(project) -> script.WorkflowResult:  # pylint: disable=unused-argument
        calls.append("data")
        return script.WorkflowResult(name="data", passed=True)

    monkeypatch.setattr(script, "run_data_validation", fake_run_data_validation)

    exit_code = script.main([str(project_file), "--workflow", "data"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert calls == ["data"]
    assert "Data" in output


def test_main_skips_data_workflow_in_all_mode_when_structural_fails(monkeypatch, tmp_path, capsys):
    project_file = tmp_path / "shapeshifter.yml"
    project_file.write_text("metadata: {}\nentities: {}\n", encoding="utf-8")

    calls: list[str] = []

    monkeypatch.setattr(script, "setup_logging", lambda **kwargs: None)
    monkeypatch.setattr(script, "load_project", lambda project_path, env_file: object())
    monkeypatch.setattr(
        script,
        "run_structural_validation",
        lambda project: script.WorkflowResult(name="structural", passed=False, errors=["broken structure"]),
    )
    monkeypatch.setattr(
        script,
        "run_conformance_validation",
        lambda project: script.WorkflowResult(name="conformance", passed=True),
    )

    async def fake_run_data_validation(project):  # pylint: disable=unused-argument
        calls.append("data")
        return script.WorkflowResult(name="data", passed=True)

    monkeypatch.setattr(script, "run_data_validation", fake_run_data_validation)

    exit_code = script.main([str(project_file), "--workflow", "all"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert not calls
    assert "Skipped because structural validation reported errors." in output


def test_main_accepts_target_model_conformance_alias(monkeypatch, tmp_path):
    project_file = tmp_path / "shapeshifter.yml"
    project_file.write_text("metadata: {}\nentities: {}\n", encoding="utf-8")

    calls: list[str] = []

    monkeypatch.setattr(script, "setup_logging", lambda **kwargs: None)
    monkeypatch.setattr(script, "load_project", lambda project_path, env_file: object())
    monkeypatch.setattr(
        script,
        "run_structural_validation",
        lambda project: (_ for _ in ()).throw(AssertionError("structural workflow should not run")),
    )

    async def fake_run_data_validation(project):
        raise AssertionError("data workflow should not run")

    monkeypatch.setattr(script, "run_data_validation", fake_run_data_validation)

    def fake_run_conformance_validation(project):  # pylint: disable=unused-argument
        calls.append("conformance")
        return script.WorkflowResult(name="conformance", passed=True)

    monkeypatch.setattr(script, "run_conformance_validation", fake_run_conformance_validation)

    exit_code = script.main([str(project_file), "--workflow", "target-model-conformance"])

    assert exit_code == 0
    assert calls == ["conformance"]
