from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .detect import detect_project


POWERSHELL = "powershell.exe"
WT = "wt.exe"


@dataclass(frozen=True)
class ProjectState:
    path: Path
    exists: bool
    is_empty: bool
    has_git: bool
    initialized: bool
    stacks: tuple[str, ...]
    alert_path: Path | None

    @property
    def kind(self) -> str:
        if not self.exists or self.is_empty:
            return "nuevo"
        return "existente"


@dataclass(frozen=True)
class LaunchPlan:
    executable: str
    args: tuple[str, ...]

    def command(self) -> list[str]:
        return [self.executable, *self.args]


@dataclass(frozen=True)
class WorkbenchSelectionPlan:
    project: ProjectState
    init_args: tuple[str, ...] | None
    guard_args: tuple[str, ...] | None
    git_message: str | None
    terminal_plans: tuple[LaunchPlan, LaunchPlan]


WORKBENCH_V2_TOPBAR_CONTROLS = (
    "Recientes",
    "Proyecto",
    "Buscar...",
    "Diagnóstico",
    "Alerta",
    "↻",
)
WORKBENCH_V2_MAIN_AREAS = ("Codex CLI", "PowerShell manual")
WORKBENCH_V2_OBSOLETE_MAIN_CONTROLS = (
    "Auto init",
    "Auto guard",
    "Windows Terminal",
    "Inicializar Toolkit",
    "Doctor",
    "Guard Check",
    "Statusbar",
    "Abrir Codex",
    "Abrir PowerShell",
    "Abrir Workbench 3 paneles",
    "Abrir carpeta",
    "Refrescar estado",
)


def find_executable(name: str) -> str | None:
    return shutil.which(name)


def codex_available() -> bool:
    return find_executable("codex") is not None


def windows_terminal_available() -> bool:
    return find_executable(WT) is not None


def inspect_project(path: str | os.PathLike[str]) -> ProjectState:
    project = Path(path).expanduser().resolve()
    exists = project.exists()
    is_empty = True
    has_git = False
    stacks: tuple[str, ...] = ()
    initialized = False
    if exists and project.is_dir():
        try:
            is_empty = next(project.iterdir(), None) is None
        except OSError:
            is_empty = False
        detection = detect_project(project)
        has_git = detection.has_git
        stacks = detection.stacks
        initialized = any((project / name).exists() for name in ("AGENTS.md", ".codex", ".rtk"))
    alert = project / ".llm-toolkit" / "alerts" / "CODEX_ALERT.md"
    return ProjectState(
        path=project,
        exists=exists,
        is_empty=is_empty,
        has_git=has_git,
        initialized=initialized,
        stacks=stacks,
        alert_path=alert if alert.exists() else None,
    )


def ensure_project_dir(path: str | os.PathLike[str]) -> Path:
    project = Path(path).expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    return project


def init_toolkit_args(caveman_level: str = "lite") -> tuple[str, ...]:
    return ("init", "--rtk", "--caveman", caveman_level, "--codeburn")


def guard_check_args() -> tuple[str, ...]:
    return ("guard", "check", "--write-alert")


def diagnostic_commands() -> tuple[tuple[str, ...], ...]:
    return (
        ("doctor",),
        ("env",),
        ("stale", "status"),
        ("statusbar",),
    )


def read_alert_text(project: Path) -> str | None:
    alert = project / ".llm-toolkit" / "alerts" / "CODEX_ALERT.md"
    if not alert.exists():
        return None
    try:
        return alert.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        return f"No se pudo leer la alerta: {exc}"


def ps_quote(value: str | os.PathLike[str]) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def venv_path_prefix_script(project: Path) -> str:
    scripts = project / ".venv" / "Scripts"
    if not scripts.exists():
        return ""
    return f"$env:Path = {ps_quote(str(scripts))} + ';' + $env:Path; "


def recommended_commands_script(stacks: tuple[str, ...] = ()) -> str:
    commands = [
        "llm-toolkit env",
        "llm-toolkit doctor",
        "llm-toolkit statusbar",
        "rtk git status",
        "rtk git diff --stat",
        "rtk git diff --name-only",
        "rtk gain",
    ]
    if "python" in stacks:
        commands.append("rtk pytest -p no:cacheprovider")
    if "flutter" in stacks:
        commands.extend(
            [
                "flutter test --reporter compact",
                "flutter analyze --no-pub",
                "rtk flutter test",
                "rtk flutter analyze",
            ]
        )
    if "dart" in stacks:
        commands.extend(
            [
                "dart test --reporter compact",
                "rtk dart test",
                "rtk dart analyze",
            ]
        )
    lines = ["Comandos recomendados:"]
    lines.extend(f"  {command}" for command in commands)
    return "$commands = @(" + ",".join(ps_quote(line) for line in lines) + "); $commands | ForEach-Object { Write-Host $_ }"


def powershell_script(project: Path, body: str, *, include_venv: bool = True) -> str:
    prefix = venv_path_prefix_script(project) if include_venv else ""
    return f"Set-Location -LiteralPath {ps_quote(project)}; {prefix}{body}"


def powershell_plan(project: Path, body: str, *, include_venv: bool = True) -> LaunchPlan:
    script = powershell_script(project, body, include_venv=include_venv)
    return LaunchPlan(POWERSHELL, ("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", script))


def codex_plan(project: Path) -> LaunchPlan:
    body = "llm-toolkit guard check --write-alert; if ($LASTEXITCODE -ne 0) { Write-Host 'Guard devolvió un error; revisar salida.' }; codex"
    return powershell_plan(project, body)


def manual_powershell_plan(project: Path, stacks: tuple[str, ...] = ()) -> LaunchPlan:
    return powershell_plan(project, recommended_commands_script(stacks))


def two_terminal_plans(project: Path, stacks: tuple[str, ...] = ()) -> tuple[LaunchPlan, LaunchPlan]:
    return (codex_plan(project), manual_powershell_plan(project, stacks))


def build_project_selection_plan(
    path: str | os.PathLike[str],
    *,
    caveman_level: str = "lite",
    auto_init: bool = True,
    auto_guard: bool = True,
) -> WorkbenchSelectionPlan:
    state = inspect_project(path)
    git_message = None if state.has_git or not state.exists else "Git no detectado; git init manual"
    init_args = init_toolkit_args(caveman_level) if auto_init and (not state.exists or state.is_empty or not state.initialized) else None
    guard_args = guard_check_args() if auto_guard else None
    return WorkbenchSelectionPlan(
        project=state,
        init_args=init_args,
        guard_args=guard_args,
        git_message=git_message,
        terminal_plans=two_terminal_plans(state.path, state.stacks),
    )


def statusbar_plan(project: Path) -> LaunchPlan:
    return powershell_plan(project, "llm-toolkit statusbar --watch --interval 5")


def folder_plan(project: Path) -> LaunchPlan:
    return LaunchPlan("explorer.exe", (str(project),))


def _wt_panel_args(title: str, project: Path, body: str) -> tuple[str, ...]:
    return (
        "--title",
        title,
        "-d",
        str(project),
        POWERSHELL,
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        powershell_script(project, body),
    )


def windows_terminal_three_panel_plan(project: Path, *, include_statusbar: bool = True, stacks: tuple[str, ...] = ()) -> LaunchPlan:
    args: list[str] = ["new-tab", *_wt_panel_args("Codex", project, "llm-toolkit guard check --write-alert; codex")]
    args.extend([";", "split-pane", "-V", *_wt_panel_args("PowerShell", project, recommended_commands_script(stacks))])
    if include_statusbar:
        args.extend([";", "split-pane", "-H", *_wt_panel_args("Statusbar", project, "llm-toolkit statusbar --watch --interval 5")])
    return LaunchPlan(WT, tuple(args))


def fallback_three_powershell_plans(project: Path, *, include_statusbar: bool = True, stacks: tuple[str, ...] = ()) -> tuple[LaunchPlan, ...]:
    plans = [codex_plan(project), manual_powershell_plan(project, stacks)]
    if include_statusbar:
        plans.append(statusbar_plan(project))
    return tuple(plans)


def workbench_three_panel_plans(
    project: Path,
    *,
    prefer_windows_terminal: bool = True,
    include_statusbar: bool = True,
    stacks: tuple[str, ...] = (),
) -> tuple[LaunchPlan, ...]:
    if prefer_windows_terminal and windows_terminal_available():
        return (windows_terminal_three_panel_plan(project, include_statusbar=include_statusbar, stacks=stacks),)
    return fallback_three_powershell_plans(project, include_statusbar=include_statusbar, stacks=stacks)


def launch_plan(plan: LaunchPlan) -> subprocess.Popen:
    return subprocess.Popen(plan.command())


def launch_plans(plans: tuple[LaunchPlan, ...]) -> list[subprocess.Popen]:
    return [launch_plan(plan) for plan in plans]


def launch_workbench(
    *,
    project: str | None = None,
    auto_init: bool = True,
    auto_guard: bool = True,
    caveman_level: str = "lite",
    open_statusbar: bool = True,
) -> int:
    try:
        from .workbench_app import run_workbench
    except ImportError as exc:
        raise RuntimeError(
            "PySide6 no está instalado. Instalar con:\n"
            "python -m pip install -e .[gui]\n"
            "o, si usa pipx:\n"
            "pipx inject llm-toolkit PySide6"
        ) from exc
    return run_workbench(
        project=project,
        auto_init=auto_init,
        auto_guard=auto_guard,
        caveman_level=caveman_level,
        open_statusbar=open_statusbar,
    )
