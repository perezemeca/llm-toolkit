from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from typer.testing import CliRunner

from llm_toolkit.codex_hooks import get_codex_hook_status
from llm_toolkit.cli import app


runner = CliRunner()


def invoke_in_path(tmp_path: Path, args: list[str], monkeypatch) -> object:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return runner.invoke(app, args)


def test_init_codeburn_crea_config_con_hooks_true(tmp_path: Path, monkeypatch) -> None:
    result = invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)

    assert result.exit_code == 0
    config = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "[features]" in config
    assert "hooks = true" in config
    assert "codex_hooks" not in config


def test_init_codeburn_preserva_config_existente(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text('[model]\nname = "gpt-test"\n\n[features]\nfoo = true\ncodex_hooks = false\n', encoding="utf-8")

    result = invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)

    assert result.exit_code == 0
    config = config_path.read_text(encoding="utf-8")
    assert '[model]\nname = "gpt-test"' in config
    assert "foo = true" in config
    assert "hooks = true" in config
    assert "codex_hooks = false" not in config
    assert config.count("[features]") == 1


def test_init_codeburn_migra_codex_hooks_true_a_hooks_true(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text('[model]\nname = "gpt-test"\n\n[features]\nfoo = true\ncodex_hooks = true\n', encoding="utf-8")

    result = invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)

    assert result.exit_code == 0
    config = config_path.read_text(encoding="utf-8")
    assert '[model]\nname = "gpt-test"' in config
    assert "foo = true" in config
    assert "hooks = true" in config
    assert "codex_hooks" not in config
    assert config.count("[features]") == 1


def test_init_codeburn_crea_hooks_json_y_script(tmp_path: Path, monkeypatch) -> None:
    result = invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)

    assert result.exit_code == 0
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / ".codex" / "hooks" / "llm_toolkit_guard_hook.py").exists()


def test_doctor_detecta_automatizacion_codeburn_guard_ok(tmp_path: Path, monkeypatch) -> None:
    invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)

    status = get_codex_hook_status(tmp_path)
    report = invoke_in_path(tmp_path, ["doctor"], monkeypatch)

    assert status.automation_ok is True
    assert report.exit_code == 0
    assert "automatización CodeBurn Guard" in report.output
    assert "configurada" in report.output
    assert "hooks habilitado" in report.output
    assert "true" in report.output


def test_doctor_detecta_codex_hooks_true_como_legacy(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    hooks_json_path = tmp_path / ".codex" / "hooks.json"
    hook_script_path = tmp_path / ".codex" / "hooks" / "llm_toolkit_guard_hook.py"
    config_path.parent.mkdir()
    hook_script_path.parent.mkdir()
    config_path.write_text("[features]\ncodex_hooks = true\n", encoding="utf-8")
    hooks_json_path.write_text("{}\n", encoding="utf-8")
    hook_script_path.write_text("print('ok')\n", encoding="utf-8")

    status = get_codex_hook_status(tmp_path)
    report = invoke_in_path(tmp_path, ["status"], monkeypatch)

    assert status.hooks_enabled is False
    assert status.legacy_hooks_enabled is True
    assert status.migration_needed is True
    assert status.automation_ok is True
    assert report.exit_code == 0
    assert "hooks habilitado" in report.output
    assert "legacy/deprecated" in report.output
    assert "llm-toolkit init --codeburn" in report.output


def test_hooks_json_contiene_eventos_requeridos(tmp_path: Path, monkeypatch) -> None:
    invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)

    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    hooks = data["hooks"]

    assert "SessionStart" in hooks
    assert "UserPromptSubmit" in hooks
    assert "PostToolUse" in hooks
    assert "Stop" in hooks


def test_hook_script_no_falla_con_payload_vacio(tmp_path: Path, monkeypatch) -> None:
    invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)
    script = tmp_path / ".codex" / "hooks" / "llm_toolkit_guard_hook.py"

    result = subprocess.run(
        ["python", str(script), "stop"],
        cwd=tmp_path,
        input="",
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert (tmp_path / ".llm-toolkit" / "state" / "guard_hook_state.json").exists()


def test_hook_script_detecta_pytest_y_dispara_guard_check(tmp_path: Path, monkeypatch) -> None:
    invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "guard-called.txt"
    (bin_dir / "llm-toolkit.cmd").write_text(f"@echo off\r\necho called > \"{marker}\"\r\nexit /b 0\r\n", encoding="utf-8")
    script = tmp_path / ".codex" / "hooks" / "llm_toolkit_guard_hook.py"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    payload = {"tool_input": {"command": "python -m pytest -p no:cacheprovider"}}

    result = subprocess.run(
        ["python", str(script), "post_tool_use"],
        cwd=tmp_path,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )

    assert result.returncode == 0
    assert marker.exists()


def test_hook_script_detecta_flutter_y_dart_test_analyze(tmp_path: Path, monkeypatch) -> None:
    for command in ("flutter test", "dart test", "flutter analyze", "dart analyze"):
        project = tmp_path / command.replace(" ", "-")
        project.mkdir()
        invoke_in_path(project, ["init", "--codeburn"], monkeypatch)
        bin_dir = project / "bin"
        bin_dir.mkdir()
        marker = project / "guard-called.txt"
        (bin_dir / "llm-toolkit.cmd").write_text(f"@echo off\r\necho called > \"{marker}\"\r\nexit /b 0\r\n", encoding="utf-8")
        script = project / ".codex" / "hooks" / "llm_toolkit_guard_hook.py"
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
        payload = {"tool_input": {"command": command}}

        result = subprocess.run(
            ["python", str(script), "post_tool_use"],
            cwd=project,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )

        assert result.returncode == 0
        assert marker.exists()


def test_init_codeburn_es_idempotente_y_no_reescribe_hooks_identicos(tmp_path: Path, monkeypatch) -> None:
    first = invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)
    assert first.exit_code == 0
    paths = [
        tmp_path / ".codex" / "config.toml",
        tmp_path / ".codex" / "hooks.json",
        tmp_path / ".codex" / "hooks" / "llm_toolkit_guard_hook.py",
    ]
    mtimes = [path.stat().st_mtime_ns for path in paths]
    time.sleep(0.02)

    second = invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)

    assert second.exit_code == 0
    assert [path.stat().st_mtime_ns for path in paths] == mtimes
