from pathlib import Path

from typer.testing import CliRunner

from llm_toolkit.caveman import CAVEMAN_BEGIN, detect_level, get_status
from llm_toolkit.cli import app
from llm_toolkit.doctor import build_report


runner = CliRunner()


def invoke_in_path(tmp_path: Path, args: list[str], monkeypatch) -> object:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return runner.invoke(app, args)


def test_init_caveman_crea_bloque_en_agents(tmp_path: Path, monkeypatch) -> None:
    result = invoke_in_path(tmp_path, ["init", "--caveman"], monkeypatch)

    assert result.exit_code == 0
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert CAVEMAN_BEGIN in content
    assert "- Nivel configurado: lite" in content


def test_init_caveman_no_duplica_bloque(tmp_path: Path, monkeypatch) -> None:
    invoke_in_path(tmp_path, ["init", "--caveman"], monkeypatch)
    invoke_in_path(tmp_path, ["init", "--caveman"], monkeypatch)

    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert content.count(CAVEMAN_BEGIN) == 1


def test_init_caveman_full_reemplaza_nivel_lite(tmp_path: Path, monkeypatch) -> None:
    invoke_in_path(tmp_path, ["init", "--caveman"], monkeypatch)
    result = invoke_in_path(tmp_path, ["init", "--caveman", "full"], monkeypatch)

    assert result.exit_code == 0
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "- Nivel configurado: full" in content
    assert "- Nivel configurado: lite" not in content
    assert detect_level(tmp_path) == "full"


def test_init_caveman_crea_skill_con_frontmatter_valido(tmp_path: Path, monkeypatch) -> None:
    result = invoke_in_path(tmp_path, ["init", "--caveman"], monkeypatch)

    assert result.exit_code == 0
    skill = tmp_path / ".agents" / "skills" / "caveman-codex" / "SKILL.md"
    raw = skill.read_bytes()
    assert raw.startswith(b"---")
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert "name: caveman-codex" in skill.read_text(encoding="utf-8")


def test_doctor_detecta_caveman_configurado(tmp_path: Path, monkeypatch) -> None:
    invoke_in_path(tmp_path, ["init", "--caveman", "ultra"], monkeypatch)

    report = build_report(tmp_path)
    status = get_status(tmp_path)

    assert any(check.name == "Caveman configurado" and check.ok for check in report.checks)
    assert any(check.name == "nivel Caveman" and check.detail == "ultra" for check in report.checks)
    assert status.configured is True
    assert status.skill_exists is True
    assert status.skill_frontmatter_valid is True
    assert status.level == "ultra"


def test_status_muestra_caveman_sin_fallar(tmp_path: Path, monkeypatch) -> None:
    invoke_in_path(tmp_path, ["init", "--caveman"], monkeypatch)

    result = invoke_in_path(tmp_path, ["status"], monkeypatch)

    assert result.exit_code == 0
    assert "llm-toolkit status" in result.output
    assert "Caveman configurado" in result.output
    assert "Comandos recomendados - Caveman" in result.output
    assert "Nivel actual:" in result.output
    assert "llm-toolkit init --caveman full" in result.output
    assert "$caveman full" in result.output


def test_doctor_sugiere_init_caveman_si_no_esta_configurado(tmp_path: Path, monkeypatch) -> None:
    result = invoke_in_path(tmp_path, ["doctor"], monkeypatch)

    assert result.exit_code == 0
    assert "Comandos recomendados - RTK" in result.output
    assert "Comandos recomendados - Caveman" in result.output
    assert "Caveman no configurado" in result.output
    assert "llm-toolkit init --caveman lite" in result.output
    assert "Caveman aplica únicamente al modo compacto de programación con Codex" in result.output


def test_init_rtk_caveman_mantiene_ambos_bloques(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git" / "info").mkdir(parents=True)

    result = invoke_in_path(tmp_path, ["init", "--rtk", "--caveman"], monkeypatch)

    assert result.exit_code == 0
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- LLM-TOOLKIT:RTK:BEGIN -->" in content
    assert "<!-- LLM-TOOLKIT:CAVEMAN:BEGIN -->" in content
