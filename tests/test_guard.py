from pathlib import Path

from typer.testing import CliRunner

from llm_toolkit import guard
from llm_toolkit.cli import app
from llm_toolkit.stale import StaleReport


runner = CliRunner()


def invoke_in_path(tmp_path: Path, args: list[str], monkeypatch) -> object:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return runner.invoke(app, args)


def test_guard_check_sin_codeburn_no_falla(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "run_codeburn_optimize", lambda timeout=30: (False, None, "CodeBurn no está instalado."))

    result = invoke_in_path(tmp_path, ["guard", "check"], monkeypatch)

    assert result.exit_code == 0
    assert "UNKNOWN" in result.output
    state = tmp_path / ".llm-toolkit" / "state" / "context_health.json"
    assert state.exists()


def test_guard_check_con_context_heavy_genera_warning(tmp_path: Path, monkeypatch) -> None:
    output = "Potential savings: ~100K tokens\n2 context-heavy sessions"
    monkeypatch.setattr(guard, "run_codeburn_optimize", lambda timeout=30: (True, 0, output))

    result = invoke_in_path(tmp_path, ["guard", "check"], monkeypatch)

    assert result.exit_code == 0
    assert "WARNING" in result.output
    state = (tmp_path / ".llm-toolkit" / "state" / "context_health.json").read_text(encoding="utf-8")
    assert '"level": "WARNING"' in state


def test_guard_check_write_alert_crea_codex_alert(tmp_path: Path, monkeypatch) -> None:
    output = "1 context-heavy sessions ------------------------- High ---\n(55.2:1)"
    monkeypatch.setattr(guard, "run_codeburn_optimize", lambda timeout=30: (True, 0, output))

    result = invoke_in_path(tmp_path, ["guard", "check", "--write-alert"], monkeypatch)

    assert result.exit_code == 0
    assert "CRITICAL" in result.output
    alert = tmp_path / ".llm-toolkit" / "alerts" / "CODEX_ALERT.md"
    assert alert.exists()
    assert "Regla de contexto fresco" in alert.read_text(encoding="utf-8")


def test_guard_check_incluye_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "run_codeburn_optimize", lambda timeout=30: (False, None, "CodeBurn no está instalado."))
    monkeypatch.setattr(
        guard,
        "check_stale",
        lambda root: StaleReport("OK", "sin cambios", (), "OK", "Env OK", "fingerprint", None),
    )

    result = invoke_in_path(tmp_path, ["guard", "check"], monkeypatch)

    state = (tmp_path / ".llm-toolkit" / "state" / "context_health.json").read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert '"environment"' in state
    assert '"level": "OK"' in state


def test_guard_write_alert_genera_environment_stale(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "run_codeburn_optimize", lambda timeout=30: (False, None, "CodeBurn no está instalado."))
    monkeypatch.setattr(
        guard,
        "check_stale",
        lambda root: StaleReport("STALE", "cambió AGENTS.md", ("AGENTS.md",), "OK", "Env OK", "fingerprint", None),
    )

    result = invoke_in_path(tmp_path, ["guard", "check", "--write-alert"], monkeypatch)

    alert = tmp_path / ".llm-toolkit" / "alerts" / "CODEX_ALERT.md"
    assert result.exit_code == 0
    assert alert.exists()
    assert "Environment STALE" in alert.read_text(encoding="utf-8")


def test_guard_no_bloquea_si_envcheck_falla(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "run_codeburn_optimize", lambda timeout=30: (False, None, "CodeBurn no está instalado."))

    def fail(root):
        raise RuntimeError("falló env")

    monkeypatch.setattr(guard, "check_stale", fail)

    result = invoke_in_path(tmp_path, ["guard", "check"], monkeypatch)

    assert result.exit_code == 0
    state = (tmp_path / ".llm-toolkit" / "state" / "context_health.json").read_text(encoding="utf-8")
    assert "Chequeo de entorno no disponible" in state


def test_guard_excluye_llm_toolkit(tmp_path: Path) -> None:
    path = guard.ensure_guard_excluded(tmp_path)

    assert path == tmp_path / ".gitignore"
    assert ".llm-toolkit/" in path.read_text(encoding="utf-8")


def test_guard_start_status_stop_no_dejan_procesos(tmp_path: Path, monkeypatch) -> None:
    start = invoke_in_path(tmp_path, ["guard", "start", "--interval", "300", "--timeout", "30"], monkeypatch)
    status = invoke_in_path(tmp_path, ["guard", "status"], monkeypatch)
    stop = invoke_in_path(tmp_path, ["guard", "stop"], monkeypatch)
    status_after_stop = invoke_in_path(tmp_path, ["guard", "status"], monkeypatch)

    assert start.exit_code == 0
    assert status.exit_code == 0
    assert '"active": true' in status.output
    assert stop.exit_code == 0
    assert status_after_stop.exit_code == 0
    assert '"active": false' in status_after_stop.output
