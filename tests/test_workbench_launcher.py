from pathlib import Path

from typer.testing import CliRunner

from llm_toolkit import cli
from llm_toolkit.cli import app
from llm_toolkit.workbench_launcher import (
    WORKBENCH_V2_MAIN_AREAS,
    WORKBENCH_V2_OBSOLETE_MAIN_CONTROLS,
    WORKBENCH_V2_TOPBAR_CONTROLS,
    build_project_selection_plan,
    codex_available,
    diagnostic_commands,
    inspect_project,
    init_toolkit_args,
    manual_powershell_plan,
    ps_quote,
    read_alert_text,
    two_terminal_plans,
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


def test_workbench_v2_layout_expone_topbar_y_dos_areas_principales() -> None:
    assert WORKBENCH_V2_TOPBAR_CONTROLS == ("Recientes", "Proyecto", "Buscar...", "Diagnóstico", "Alerta", "↻")
    assert WORKBENCH_V2_MAIN_AREAS == ("Codex CLI", "PowerShell manual")
    assert "Auto init" in WORKBENCH_V2_OBSOLETE_MAIN_CONTROLS
    assert "Abrir PowerShell" in WORKBENCH_V2_OBSOLETE_MAIN_CONTROLS


def test_seleccion_de_proyecto_dispara_init_guard_y_dos_terminales(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()

    plan = build_project_selection_plan(project, caveman_level="lite")

    assert plan.init_args == init_toolkit_args("lite")
    assert plan.guard_args == ("guard", "check", "--write-alert")
    assert plan.git_message == "Git no detectado; git init manual"
    assert len(plan.terminal_plans) == 2
    assert "git init" not in " ".join(plan.terminal_plans[0].command())


def test_seleccion_no_reinicializa_si_ya_hay_toolkit(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    (project / "AGENTS.md").write_text("# demo\n", encoding="utf-8")

    plan = build_project_selection_plan(project, caveman_level="full")

    assert plan.init_args is None
    assert plan.guard_args == ("guard", "check", "--write-alert")


def test_comandos_codex_y_powershell_usan_ruta_del_proyecto(tmp_path: Path) -> None:
    project = tmp_path / "repo con espacios"
    (project / ".venv" / "Scripts").mkdir(parents=True)

    codex, shell = two_terminal_plans(project, ("python",))
    codex_script = codex.command()[-1]
    shell_script = shell.command()[-1]

    assert str(project) in codex_script
    assert str(project) in shell_script
    assert "llm-toolkit guard check --write-alert" in codex_script
    assert "codex" in codex_script
    assert str(project / ".venv" / "Scripts") in shell_script
    assert "rtk pytest -p no:cacheprovider" in shell_script


def test_alerta_se_lee_para_dialogo_interno(tmp_path: Path) -> None:
    alert = tmp_path / ".llm-toolkit" / "alerts" / "CODEX_ALERT.md"
    alert.parent.mkdir(parents=True)
    alert.write_text("# CODEX ALERT\n\nEstado: CRITICAL\n", encoding="utf-8")

    assert read_alert_text(tmp_path) == "# CODEX ALERT\n\nEstado: CRITICAL\n"


def test_diagnostico_agrupa_comandos_secundarios() -> None:
    commands = diagnostic_commands()

    assert ("doctor",) in commands
    assert ("env",) in commands
    assert ("stale", "status") in commands
    assert ("statusbar",) in commands
