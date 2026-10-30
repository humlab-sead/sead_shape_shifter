from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from subprocess import CompletedProcess

import pytest

MODULE_SPEC = spec_from_file_location(
    "update_pr_descriptions",
    Path(__file__).resolve().parents[1] / "update_pr_descriptions.py",
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError("Could not load update_pr_descriptions.py")
update_pr_descriptions = module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(update_pr_descriptions)


VALID_BODY = """## Summary
Changed.

## User-facing release note
None.

## Upgrade notes
None - no user action required.

## Validation
Not verified: validation results unavailable."""


def make_draft(title: str = "Example PR title") -> dict[str, str]:
    return update_pr_descriptions.validate_draft({"title": title, "body": VALID_BODY})


def test_pr_specs_expand_inclusive_ranges_and_remove_duplicates() -> None:
    assert update_pr_descriptions.parse_pr_specs(["620-622", "622", "625"]) == [620, 621, 622, 625]


def test_parse_copilot_response_preserves_multiline_markdown_and_quotes() -> None:
    body = VALID_BODY.replace("Changed.", 'Changed "field" across\nmultiple lines.')
    response = f"Example PR title\n{update_pr_descriptions.COPILOT_BODY_SEPARATOR}\n{body}"

    assert update_pr_descriptions.parse_copilot_response(response) == {"title": "Example PR title", "body": body}


@pytest.mark.parametrize("verbose", [False, True])
def test_generate_draft_logs_invalid_response_only_when_verbose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    verbose: bool,
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(update_pr_descriptions, "render_context", lambda context: "context")
    monkeypatch.setattr(
        update_pr_descriptions,
        "configure_copilot_environment",
        lambda model: ("test-model", {"COPILOT_PROVIDER_API_KEY": "test-key"}),
    )
    monkeypatch.setattr(update_pr_descriptions, "run_command", lambda *args, **kwargs: "malformed test-key response")

    with pytest.raises(ValueError, match="after the title"):
        update_pr_descriptions.generate_draft({}, None, verbose=verbose)

    logged = capsys.readouterr().err
    if verbose:
        assert "Raw Copilot response:" in logged
        assert "malformed [REDACTED] response" in logged
        assert "test-key" not in logged
    else:
        assert logged == ""


def test_run_command_reports_empty_stdout_and_redacts_provider_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        update_pr_descriptions.subprocess,
        "run",
        lambda command, **kwargs: CompletedProcess(command, 0, stdout="", stderr="provider rejected test-key"),
    )

    with pytest.raises(update_pr_descriptions.CommandError) as error:
        update_pr_descriptions.run_command(
            ["copilot", "-p", "draft"],
            env={"COPILOT_PROVIDER_API_KEY": "test-key"},
            require_stdout=True,
        )

    assert "provider rejected [REDACTED]" in str(error.value)
    assert "test-key" not in str(error.value)


@pytest.mark.parametrize(
    ("requested_model", "expected_model"),
    [(None, "dotenv-model"), ("other-model", "other-model")],
)
def test_generate_draft_uses_configured_model_and_passes_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requested_model: str | None,
    expected_model: str,
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(update_pr_descriptions, "render_context", lambda context: "context")
    (tmp_path / ".env").write_text(
        "PR_DESCRIPTION_DEFAULT_MODEL=dotenv-model\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE=openai\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL=http://localhost:9000/v1\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY=dotenv-secret\n",
        encoding="utf-8",
    )
    for key in (
        "COPILOT_PROVIDER_TYPE",
        "COPILOT_PROVIDER_BASE_URL",
        "COPILOT_PROVIDER_MODEL_ID",
        "COPILOT_PROVIDER_WIRE_MODEL",
        "PR_DESCRIPTION_DEFAULT_MODEL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("COPILOT_PROVIDER_API_KEY", "configured-key")
    captured: dict[str, object] = {}

    def fake_run_command(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        require_stdout: bool = False,
    ) -> str:
        captured["command"] = command
        captured["environment"] = env
        captured["working_directory"] = cwd
        captured["require_stdout"] = require_stdout
        draft = make_draft()
        return f"{draft['title']}\n{update_pr_descriptions.COPILOT_BODY_SEPARATOR}\n{draft['body']}"

    monkeypatch.setattr(update_pr_descriptions, "run_command", fake_run_command)

    update_pr_descriptions.generate_draft({}, requested_model)

    command = captured["command"]
    environment = captured["environment"]
    working_directory = captured["working_directory"]
    assert isinstance(command, list)
    assert command[command.index("--model") + 1] == expected_model
    assert command[command.index("--stream") + 1] == "off"
    assert command[command.index("--secret-env-vars") + 1] == "COPILOT_PROVIDER_API_KEY"
    assert captured["require_stdout"] is True
    assert isinstance(environment, dict)
    assert isinstance(working_directory, Path)
    assert working_directory.parent == tmp_path / "tmp"
    assert working_directory.name.startswith("pr-description-")
    assert not working_directory.exists()
    assert environment["COPILOT_PROVIDER_TYPE"] == "openai"
    assert environment["COPILOT_PROVIDER_BASE_URL"] == "http://localhost:9000/v1"
    assert environment["COPILOT_PROVIDER_MODEL_ID"] == expected_model
    assert environment["COPILOT_PROVIDER_WIRE_MODEL"] == expected_model
    assert environment["COPILOT_PROVIDER_API_KEY"] == "configured-key"


def test_configure_copilot_environment_reads_project_dotenv_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "REPO_ROOT", tmp_path)
    (tmp_path / ".env").write_text(
        "PR_DESCRIPTION_DEFAULT_MODEL=dotenv-model\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE=openai\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL=http://localhost:9000/v1\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY=dotenv-secret\n",
        encoding="utf-8",
    )
    for key in (
        "COPILOT_PROVIDER_MODEL_ID",
        "COPILOT_PROVIDER_WIRE_MODEL",
        "COPILOT_PROVIDER_TYPE",
        "COPILOT_PROVIDER_BASE_URL",
        "COPILOT_PROVIDER_API_KEY",
        "PR_DESCRIPTION_DEFAULT_MODEL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    model, environment = update_pr_descriptions.configure_copilot_environment(None)

    assert model == "dotenv-model"
    assert environment["COPILOT_PROVIDER_MODEL_ID"] == "dotenv-model"
    assert environment["COPILOT_PROVIDER_WIRE_MODEL"] == "dotenv-model"
    assert environment["COPILOT_PROVIDER_TYPE"] == "openai"
    assert environment["COPILOT_PROVIDER_BASE_URL"] == "http://localhost:9000/v1"
    assert environment["COPILOT_PROVIDER_API_KEY"] == "dotenv-secret"
    assert "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY" not in environment

    monkeypatch.setenv("PR_DESCRIPTION_DEFAULT_MODEL", "exported-model")
    monkeypatch.setenv("PR_DESCRIPTION_DEFAULT_PROVIDER_KEY", "exported-secret")
    exported_model, exported_environment = update_pr_descriptions.configure_copilot_environment(None)
    assert exported_model == "exported-model"
    assert exported_environment["COPILOT_PROVIDER_API_KEY"] == "exported-secret"


def test_configure_copilot_environment_fails_when_required_values_are_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "REPO_ROOT", tmp_path)
    for key in (
        "COPILOT_PROVIDER_MODEL_ID",
        "COPILOT_PROVIDER_TYPE",
        "COPILOT_PROVIDER_BASE_URL",
        "COPILOT_PROVIDER_API_KEY",
        "PR_DESCRIPTION_DEFAULT_MODEL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError, match="Missing required Copilot configuration") as error:
        update_pr_descriptions.configure_copilot_environment(None)

    assert "PR_DESCRIPTION_DEFAULT_MODEL" in str(error.value)
    assert "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE" in str(error.value)
    assert "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL" in str(error.value)
    assert "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY" in str(error.value)


def test_draft_file_format_round_trips_title_and_description() -> None:
    draft = make_draft("Title: with a colon")

    assert update_pr_descriptions.parse_draft_file(update_pr_descriptions.serialize_draft_file(draft)) == draft


def test_draft_mode_writes_files_without_publishing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    monkeypatch.setattr(update_pr_descriptions, "configure_copilot_environment", lambda model: ("test-model", {}))
    monkeypatch.setattr(update_pr_descriptions, "load_pr_context", lambda number, repo: {"number": number})
    monkeypatch.setattr(update_pr_descriptions, "generate_draft", lambda context, model, *, verbose=False: make_draft())
    monkeypatch.setattr(update_pr_descriptions, "publish_draft", lambda *args: pytest.fail("draft mode published a PR"))
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--draft"])

    assert update_pr_descriptions.main() == 0
    assert update_pr_descriptions.parse_draft_file((tmp_path / "PR_627.txt").read_text(encoding="utf-8")) == make_draft()


def test_existing_draft_is_skipped_before_configuration_or_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(
        update_pr_descriptions,
        "configure_copilot_environment",
        lambda model: pytest.fail("Copilot configuration was checked despite the existing draft"),
    )
    monkeypatch.setattr(update_pr_descriptions, "load_pr_context", lambda *args: pytest.fail("existing PR was queried"))
    monkeypatch.setattr(update_pr_descriptions, "generate_draft", lambda *args: pytest.fail("existing draft was regenerated"))
    (tmp_path / "PR_627.txt").write_text(update_pr_descriptions.serialize_draft_file(make_draft()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--draft"])

    assert update_pr_descriptions.main() == 0
    assert "Skipping PR #627 since it exists" in capsys.readouterr().err


def test_draft_batch_writes_successes_skips_existing_and_continues_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    monkeypatch.setattr(update_pr_descriptions, "configure_copilot_environment", lambda model: ("test-model", {}))
    existing_draft = make_draft("Keep this existing draft")
    (tmp_path / "PR_627.txt").write_text(update_pr_descriptions.serialize_draft_file(existing_draft), encoding="utf-8")
    queried: list[int] = []
    verbose_values: list[bool] = []

    def fake_load_pr_context(number: int, _repo: str | None) -> dict[str, int]:
        queried.append(number)
        return {"number": number}

    def fake_generate_draft(context: dict[str, int], _model: str | None, *, verbose: bool = False) -> dict[str, str]:
        verbose_values.append(verbose)
        if context["number"] == 628:
            raise ValueError("invalid Copilot response")
        return make_draft(f"Draft for PR #{context['number']}")

    monkeypatch.setattr(update_pr_descriptions, "load_pr_context", fake_load_pr_context)
    monkeypatch.setattr(update_pr_descriptions, "generate_draft", fake_generate_draft)
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627-629", "--draft"])

    assert update_pr_descriptions.main() == 1

    assert queried == [628, 629]
    assert verbose_values == [False, False]
    assert update_pr_descriptions.parse_draft_file((tmp_path / "PR_627.txt").read_text(encoding="utf-8")) == existing_draft
    assert not (tmp_path / "PR_628.txt").exists()
    assert update_pr_descriptions.parse_draft_file((tmp_path / "PR_629.txt").read_text(encoding="utf-8")) == make_draft("Draft for PR #629")
    errors = capsys.readouterr().err
    assert "Skipping PR #627 since it exists" in errors
    assert "Failed PR #628: invalid Copilot response" in errors


def test_verbose_is_rejected_for_publish_mode(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--publish", "--verbose"])

    assert update_pr_descriptions.main() == 2
    assert "--verbose can only be used with --draft." in capsys.readouterr().err


def test_publish_reads_reviewed_files_without_generating(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    draft = make_draft("Reviewed title")
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    (tmp_path / "PR_627.txt").write_text(update_pr_descriptions.serialize_draft_file(draft), encoding="utf-8")
    published: list[tuple[int, dict[str, str], str | None]] = []
    monkeypatch.setattr(update_pr_descriptions, "publish_draft", lambda number, body, repo: published.append((number, body, repo)))
    monkeypatch.setattr(
        update_pr_descriptions,
        "generate_draft",
        lambda *args: pytest.fail("publish mode regenerated a draft"),
    )
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--publish"])

    assert update_pr_descriptions.main() == 0
    assert published == [(627, draft, None)]


def test_publish_validates_every_file_before_updating_any_pr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    (tmp_path / "PR_627.txt").write_text(update_pr_descriptions.serialize_draft_file(make_draft()), encoding="utf-8")
    published: list[int] = []
    monkeypatch.setattr(update_pr_descriptions, "publish_draft", lambda number, draft, repo: published.append(number))
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627-628", "--publish"])

    assert update_pr_descriptions.main() == 1
    assert published == []
