from pathlib import Path

from typer.testing import CliRunner

from llm_toolkit import codeburn
from llm_toolkit.cli import app
from llm_toolkit.doctor import build_report


runner = CliRunner()


def invoke_in_path(tmp_path: Path, args: list[str], monkeypatch) -> object:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return runner.invoke(app, args)


def test_detect_node_devuelve_falso_si_no_existe(monkeypatch) -> None:
    monkeypatch.setattr(codeburn.shutil, "which", lambda name: None)

    status = codeburn.detect_node()

    assert status.found is False
    assert "node no encontrado" in (status.error or "")


def test_detect_npm_devuelve_falso_si_no_existe(monkeypatch) -> None:
    monkeypatch.setattr(codeburn.shutil, "which", lambda name: None)

    status = codeburn.detect_npm()

    assert status.found is False
    assert "npm no encontrado" in (status.error or "")


def test_detect_codeburn_devuelve_falso_si_no_existe(monkeypatch) -> None:
    monkeypatch.setattr(codeburn.shutil, "which", lambda name: None)

    status = codeburn.detect_codeburn()

    assert status.found is False
    assert "codeburn no encontrado" in (status.error or "")


def test_init_codeburn_agrega_bloque_en_agents(tmp_path: Path, monkeypatch) -> None:
    result = invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)

    assert result.exit_code == 0
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert codeburn.CODEBURN_BEGIN in content
    assert "codeburn status" in content


def test_init_codeburn_es_idempotente(tmp_path: Path, monkeypatch) -> None:
    invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)
    invoke_in_path(tmp_path, ["init", "--codeburn"], monkeypatch)

    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert content.count(codeburn.CODEBURN_BEGIN) == 1
    assert content.count(codeburn.CODEBURN_END) == 1


def test_doctor_status_no_fallan_sin_codeburn(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(codeburn.shutil, "which", lambda name: None)

    doctor_result = invoke_in_path(tmp_path, ["doctor"], monkeypatch)
    status_result = invoke_in_path(tmp_path, ["status"], monkeypatch)

    assert doctor_result.exit_code == 0
    assert status_result.exit_code == 0
    assert "codeburn en PATH" in doctor_result.output
    assert "Comandos recomendados - CodeBurn" in status_result.output


def test_metrics_informa_error_claro_si_codeburn_no_esta_instalado(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(codeburn.shutil, "which", lambda name: None)

    result = invoke_in_path(tmp_path, ["metrics"], monkeypatch)

    assert result.exit_code == 1
    assert "CodeBurn no está instalado. Ejecutar llm-toolkit install-codeburn." in result.output


def test_build_codeburn_agents_block_contiene_comandos_recomendados() -> None:
    block = codeburn.build_codeburn_agents_block()

    assert "codeburn status" in block
    assert "codeburn today" in block
    assert "codeburn month" in block
    assert "codeburn report -p 30days" in block
    assert "codeburn optimize" in block
    assert "No reemplaza RTK ni Caveman" in block
    assert ".llm-toolkit\\alerts\\CODEX_ALERT.md" in block
    assert "llm-toolkit guard check --write-alert" in block
    assert "regla de contexto fresco" in block
    assert "se activa automáticamente mediante Codex hooks" in block
    assert "No depender de que el usuario ejecute `guard check` manualmente" in block


def test_init_rtk_caveman_codeburn_mantiene_tres_bloques(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git" / "info").mkdir(parents=True)

    result = invoke_in_path(tmp_path, ["init", "--rtk", "--caveman", "--codeburn"], monkeypatch)

    assert result.exit_code == 0
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- LLM-TOOLKIT:RTK:BEGIN -->" in content
    assert "<!-- LLM-TOOLKIT:CAVEMAN:BEGIN -->" in content
    assert codeburn.CODEBURN_BEGIN in content


def test_build_report_incluye_estado_codeburn(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(codeburn.shutil, "which", lambda name: None)

    report = build_report(tmp_path)

    assert any(check.name == "Node en PATH" and not check.ok for check in report.checks)
    assert any(check.name == "bloque CodeBurn en AGENTS.md" for check in report.checks)
    assert "llm-toolkit metrics --json" in report.codeburn_commands
