"""Tests for scripts/generate_user_release_notes.py."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_user_release_notes.py"


def test_legacy_versioned_notes_never_include_pending_release():
    generator = load_generator_module()

    content = generator.build_release_notes(
        version="2.5.0",
        release_date="2026-10-27",
        github_repository="humlab-sead/sead_shape_shifter",
        highlights=[],
        features=[],
        improvements=[],
        fixes=[],
    )

    assert "Pending Release" not in content


def load_generator_module() -> ModuleType:
    module_name = "tests.generate_user_release_notes_module"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_legacy_ai_generator_uses_shared_provider_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    generator = load_generator_module()
    for key in (
        "COPILOT_PROVIDER_MODEL_ID",
        "COPILOT_PROVIDER_TYPE",
        "COPILOT_PROVIDER_BASE_URL",
        "COPILOT_PROVIDER_API_KEY",
        "REPO_SCRIPTS_DEFAULT_MODEL",
        "REPO_SCRIPTS_DEFAULT_PROVIDER_TYPE",
        "REPO_SCRIPTS_DEFAULT_PROVIDER_BASE_URL",
        "REPO_SCRIPTS_DEFAULT_PROVIDER_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("REPO_SCRIPTS_DEFAULT_MODEL", "configured-model")
    monkeypatch.setenv("REPO_SCRIPTS_DEFAULT_PROVIDER_TYPE", "openai")
    monkeypatch.setenv("REPO_SCRIPTS_DEFAULT_PROVIDER_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("REPO_SCRIPTS_DEFAULT_PROVIDER_KEY", "configured-key")
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self) -> bytes:
            return json.dumps({"choices": [{"message": {"content": "AI-generated draft"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout: float):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(generator.request, "urlopen", fake_urlopen)

    content, mode = generator.maybe_generate_ai_draft(
        version="2.5.0",
        release_date="2026-11-02",
        github_repository="humlab-sead/sead_shape_shifter",
        parsed_sections={},
        heuristic_draft="heuristic draft",
        force_heuristic=False,
    )

    assert content == "AI-generated draft\n"
    assert mode == "ai:configured-model"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["body"]["model"] == "configured-model"
    assert captured["authorization"] == "Bearer configured-key"
