from pathlib import Path

from typer.testing import CliRunner

from llm_toolkit import cli
from llm_toolkit.cli import app
from llm_toolkit.workbench_launcher import (
    codex_available,
    inspect_project,
    manual_powershell_plan,
    ps_quote,
    windows_terminal_three_panel_plan,
    workbench_three_panel_plans,
)


runner = CliRunner()


def test_ps_quote_escapa_rutas_con_espacios_y_comillas() -> None:
    assert ps_quote("C:\\Users\\Perez\\Mi Proyecto") == "'C:\\Users\\Perez\\Mi Proyecto'"
    assert ps_quote("C:\\O'Brien\\Repo") == "'C:\\O''Brien\\Repo'"


def test_manual_powershell_plan_incluye_venv_y_comandos(tmp_path: Path) -> None:
    project = tmp_path / "Mi Proyecto"
    (project / ".venv" / "Scripts").mkdir(parents=True)

    plan = manual_powershell_plan(project, ("python", "flutter"))
    command = plan.command()
    script = command[-1]

    assert command[0] == "powershell.exe"
    assert "Set-Location -LiteralPath" in script
    assert str(project / ".venv" / "Scripts") in script
    assert "rtk pytest -p no:cacheprovider" in script
    assert "flutter test --reporter compact" in script


def test_windows_terminal_plan_con_tres_paneles_y_statusbar(tmp_path: Path) -> None:
    project = tmp_path / "repo con espacios"
    project.mkdir()

    plan = windows_terminal_three_panel_plan(project, include_statusbar=True, stacks=("python",))
    command = plan.command()

    assert command[0] == "wt.exe"
    assert command.count(";") == 2
    assert "codex" in " ".join(command)
    assert "llm-toolkit statusbar --watch --interval 5" in " ".join(command)
    assert str(project) in command


def test_workbench_three_panel_fallback_a_powershell(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    monkeypatch.setattr("llm_toolkit.workbench_launcher.windows_terminal_available", lambda: False)

    plans = workbench_three_panel_plans(project, prefer_windows_terminal=True, include_statusbar=False)

    assert len(plans) == 2
    assert all(plan.executable == "powershell.exe" for plan in plans)


def test_codex_available_usa_path(monkeypatch) -> None:
    monkeypatch.setattr("llm_toolkit.workbench_launcher.find_executable", lambda name: "C:\\tools\\codex.exe" if name == "codex" else None)

    assert codex_available() is True


def test_inspect_project_detecta_existente_sin_git(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    state = inspect_project(tmp_path)

    assert state.exists is True
    assert state.kind == "existente"
    assert state.has_git is False
    assert state.stacks == ("python",)


def test_workbench_help_no_importa_pyside() -> None:
    result = runner.invoke(app, ["workbench", "--help"])

    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--no-init" in result.output
    assert "--no-guard" in result.output


def test_workbench_cli_pasa_opciones(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    def fake_launch(**kwargs):
        calls.update(kwargs)
        return 0

    monkeypatch.setattr(cli, "launch_workbench", fake_launch)
    result = runner.invoke(
        app,
        [
            "workbench",
            "--project",
            str(tmp_path),
            "--no-init",
            "--no-guard",
            "--caveman-level",
            "full",
            "--no-statusbar",
        ],
    )

    assert result.exit_code == 0
    assert calls["project"] == str(tmp_path)
    assert calls["auto_init"] is False
    assert calls["auto_guard"] is False
    assert calls["caveman_level"] == "full"
    assert calls["open_statusbar"] is False
