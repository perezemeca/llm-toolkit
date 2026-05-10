from __future__ import annotations

from importlib.resources import files as resource_files
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .caveman import DEFAULT_LEVEL, generate_agents_block, upsert_caveman_agents_block, validate_level, write_caveman_skill
from .codeburn import (
    create_or_update_codeburn_integration,
    install_codeburn_windows,
    recommended_cli_commands as recommended_codeburn_commands,
    run_codeburn_command,
)
from .detect import detect_project
from .doctor import DoctorReport, build_report
from .files import ensure_rtk_excluded, upsert_agents_block, write_text
from .guard import check_guard, read_guard_status, start_guard, stop_guard
from .rtk import configure_local_tracking, install_rtk_windows, recommended_commands


app = typer.Typer(
    help="CLI para preparar proyectos con Codex/LLM, RTK y futuras integraciones.",
    no_args_is_help=True,
    add_completion=False,
)
guard_app = typer.Typer(help="Guard liviano de CodeBurn para checkpoints de Codex.", no_args_is_help=True)
app.add_typer(guard_app, name="guard")
console = Console()


def _template(name: str) -> str:
    return resource_files("llm_toolkit").joinpath("templates", name).read_text(encoding="utf-8")


def _print_commands(title: str, commands: list[str] | tuple[str, ...]) -> None:
    console.print(f"[bold]{title}[/bold]")
    for command in commands:
        console.print(f"  [cyan]{command}[/cyan]")


def _print_command_notes(notes: list[str] | tuple[str, ...]) -> None:
    for note in notes:
        console.print(f"  {note}")


def _print_caveman_recommendations(report: DoctorReport) -> None:
    console.print("[bold]Comandos recomendados - Caveman[/bold]")
    if report.caveman.configured:
        level = report.caveman.level or "no detectado"
        console.print(f"  Nivel actual: [cyan]{level}[/cyan]")
    else:
        console.print("  Caveman no configurado. Sugerido: [cyan]llm-toolkit init --caveman lite[/cyan]")
    for command in report.caveman_commands:
        console.print(f"  [cyan]{command}[/cyan]")

    console.print("[bold]Uso en Codex[/bold]")
    for usage in report.caveman_codex_usage:
        console.print(f"  [cyan]{usage}[/cyan]")

    console.print("[bold]Reglas Caveman[/bold]")
    console.print("  Nivel recomendado por defecto: [cyan]lite[/cyan]")
    console.print("  Usar solo para reportes compactos de programación con Codex.")
    console.print("  Preservar rutas, comandos, errores exactos, nombres de tests y resultados.")
    console.print("  Caveman aplica únicamente al modo compacto de programación con Codex.")


def _print_codeburn_recommendations(report: DoctorReport) -> None:
    console.print("[bold]Comandos recomendados - CodeBurn[/bold]")
    if not report.codeburn.codeburn.found:
        console.print("  CodeBurn no instalado. Sugerido: [cyan]llm-toolkit install-codeburn[/cyan]")
    if report.codeburn.agents_block_configured:
        console.print("  Bloque CodeBurn: [cyan]configurado[/cyan]")
    else:
        console.print("  Bloque CodeBurn: [cyan]llm-toolkit init --codeburn[/cyan]")
    for command in report.codeburn_commands:
        console.print(f"  [cyan]{command}[/cyan]")


def _print_report(report: DoctorReport, title: str = "llm-toolkit doctor") -> None:
    table = Table(title=title)
    table.add_column("Revisión")
    table.add_column("Estado")
    table.add_column("Detalle")
    for check in report.checks:
        table.add_row(check.name, "OK" if check.ok else "FALTA", check.detail)
    console.print(table)
    stacks = ", ".join(report.detection.stacks) if report.detection.stacks else "unknown"
    console.print(f"Git: {'detectado' if report.detection.has_git else 'no detectado'}")
    console.print(f"Stack: {stacks}")
    _print_commands("Comandos recomendados - RTK", report.commands)
    _print_command_notes(report.command_notes)
    _print_caveman_recommendations(report)
    _print_codeburn_recommendations(report)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"llm-toolkit {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Mostrar la versión y salir.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    return None


@app.command("init")
def init_command(
    caveman_level_arg: Annotated[
        str | None,
        typer.Argument(help="Nivel Caveman opcional: lite, full o ultra."),
    ] = None,
    rtk: bool = typer.Option(False, "--rtk", help="Inicializar RTK-Codex en el proyecto actual."),
    caveman: bool = typer.Option(False, "--caveman", help="Inicializar Caveman-Codex en el proyecto actual."),
    codeburn: bool = typer.Option(False, "--codeburn", help="Inicializar integración opcional CodeBurn en AGENTS.md."),
    caveman_level: str | None = typer.Option(
        None,
        "--caveman-level",
        help="Nivel Caveman: lite, full o ultra. Por defecto: lite.",
    ),
) -> None:
    """Inicializa integraciones de llm-toolkit en el directorio actual."""
    if not rtk and not caveman and not codeburn:
        console.print("[yellow]No se indicó integración. Usá --rtk, --caveman y/o --codeburn.[/yellow]")
        raise typer.Exit(code=1)
    if caveman_level_arg is not None and not caveman:
        console.print("[red]El nivel Caveman solo puede usarse junto con --caveman.[/red]")
        raise typer.Exit(code=1)

    root = Path.cwd()
    detection = detect_project(root)
    if not detection.has_git:
        console.print("[yellow]Git no fue detectado. No se recomendarán comandos rtk git.[/yellow]")

    if rtk:
        upsert_agents_block(root, _template("AGENTS_RTK_BLOCK.md"))
        write_text(root / ".agents" / "skills" / "rtk-codex" / "SKILL.md", _template("RTK_SKILL.md"))
        write_text(root / "tools" / "codex_rtk_env.ps1", _template("codex_rtk_env.ps1"))
    llm_toolkit_doc = root / "LLM_TOOLKIT.md"
    if not llm_toolkit_doc.exists():
        write_text(llm_toolkit_doc, _template("LLM_TOOLKIT.md"))

    if rtk:
        exclude_path = ensure_rtk_excluded(root, detection.has_git)
        config = configure_local_tracking(root)
        console.print("[green]RTK-Codex inicializado.[/green]")
        console.print(f"Exclusión local configurada en: {exclude_path}")
        console.print(f"RTK usará la base local: {config.database_path}")
        console.print(f"Config RTK: {config.config_path}")
        if config.backup_path:
            console.print(f"Backup previo de config: {config.backup_path}")

    if caveman:
        requested_level = caveman_level_arg or caveman_level or DEFAULT_LEVEL
        try:
            level = validate_level(requested_level)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc
        block = generate_agents_block(level, _template("AGENTS_CAVEMAN_BLOCK.md"))
        upsert_caveman_agents_block(root, block)
        write_caveman_skill(root, _template("CAVEMAN_SKILL.md"))
        console.print(f"[green]Caveman-Codex inicializado.[/green] Nivel: {level}")

    if codeburn:
        create_or_update_codeburn_integration(root)
        console.print("[green]CodeBurn inicializado en AGENTS.md y hooks de Codex.[/green]")
        console.print("CodeBurn no se instala automáticamente y no bloquea tareas funcionales.")
        console.print("CodeBurn Guard queda automatizado para checkpoints de Codex.")
        _print_commands("Comandos recomendados - CodeBurn", recommended_codeburn_commands())

    _print_commands("Comandos recomendados - RTK", recommended_commands(detection.stacks, detection.has_git))


@app.command("doctor")
def doctor_command() -> None:
    """Revisa si el proyecto actual está preparado para llm-toolkit."""
    _print_report(build_report(Path.cwd()))


@app.command("status")
def status_command() -> None:
    """Muestra el estado de llm-toolkit en el proyecto actual."""
    _print_report(build_report(Path.cwd()), title="llm-toolkit status")


@app.command("install-rtk")
def install_rtk_command() -> None:
    """Instala rtk.exe en Windows desde GitHub Releases."""
    try:
        version = install_rtk_windows()
    except Exception as exc:
        console.print(f"[red]No se pudo instalar RTK:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]RTK instalado correctamente.[/green] {version}")


@app.command("install-codeburn")
def install_codeburn_command() -> None:
    """Instala CodeBurn con `llm-toolkit install-codeburn` si Node/npm ya están disponibles."""
    try:
        status = install_codeburn_windows()
    except Exception as exc:
        console.print(f"[red]No se pudo instalar CodeBurn:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    detail = status.version or status.path or "codeburn disponible"
    console.print(f"[green]CodeBurn instalado correctamente.[/green] {detail}")


@app.command("metrics")
def metrics_command(
    today: bool = typer.Option(False, "--today", help="Mostrar métricas de hoy."),
    month: bool = typer.Option(False, "--month", help="Mostrar métricas del mes."),
    json_output: bool = typer.Option(False, "--json", help="Mostrar reporte JSON."),
) -> None:
    """Muestra métricas locales de CodeBurn si está instalado."""
    selected = sum(1 for value in (today, month, json_output) if value)
    if selected > 1:
        console.print("[red]Usá solo una opción entre --today, --month y --json.[/red]")
        raise typer.Exit(code=1)

    args = ["status"]
    if today:
        args = ["today"]
    elif month:
        args = ["month"]
    elif json_output:
        args = ["report", "--format", "json"]

    result = run_codeburn_command(args)
    if not result.executable_found:
        console.print(f"[yellow]{result.stderr}[/yellow]")
        raise typer.Exit(code=1)
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        console.print("[yellow]CodeBurn no devolvió métricas. Puede que no haya datos locales de sesiones.[/yellow]")
        if output:
            console.print(output)
        raise typer.Exit(code=1)
    console.print(output or "[yellow]CodeBurn no devolvió datos locales de sesiones.[/yellow]")


@app.command("optimize")
def optimize_command() -> None:
    """Ejecuta recomendaciones de optimización de CodeBurn."""
    result = run_codeburn_command(["optimize"])
    if not result.executable_found:
        console.print(f"[yellow]{result.stderr}[/yellow]")
        raise typer.Exit(code=1)
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        console.print("[yellow]CodeBurn optimize falló, pero no bloquea la tarea.[/yellow]")
        if output:
            console.print(output)
        raise typer.Exit(code=1)
    console.print(output or "[yellow]CodeBurn no devolvió recomendaciones.[/yellow]")


@guard_app.command("check")
def guard_check_command(
    write_alert: bool = typer.Option(False, "--write-alert", help="Crear CODEX_ALERT.md si hay WARNING/CRITICAL."),
    timeout: int = typer.Option(30, "--timeout", min=1, help="Timeout para CodeBurn optimize en segundos."),
) -> None:
    """Ejecuta un chequeo liviano de contexto pesado con CodeBurn."""
    result = check_guard(Path.cwd(), timeout=timeout, write_alert_file=write_alert)
    console.print(f"CodeBurn Guard: [bold]{result.level}[/bold] - {result.message}")
    console.print(f"Estado: [cyan]{Path.cwd() / '.llm-toolkit' / 'state' / 'context_health.json'}[/cyan]")
    if result.alert_path:
        console.print(f"Alerta: [cyan]{result.alert_path}[/cyan]")
    if result.level in ("WARNING", "CRITICAL"):
        console.print("[yellow]Aplicar regla de contexto fresco en la próxima tarea pesada.[/yellow]")


@guard_app.command("start")
def guard_start_command(
    interval: int = typer.Option(300, "--interval", min=1, help="Intervalo sugerido entre checkpoints, en segundos."),
    timeout: int = typer.Option(30, "--timeout", min=1, help="Timeout para cada chequeo CodeBurn, en segundos."),
) -> None:
    """Registra la política de guard para checkpoints de Codex."""
    path = start_guard(Path.cwd(), interval=interval, timeout=timeout)
    console.print("[green]CodeBurn Guard iniciado en modo checkpoint.[/green]")
    console.print(f"Estado: [cyan]{path}[/cyan]")


@guard_app.command("stop")
def guard_stop_command() -> None:
    """Desactiva la política local de CodeBurn Guard."""
    path = stop_guard(Path.cwd())
    console.print("[green]CodeBurn Guard detenido.[/green]")
    console.print(f"Estado: [cyan]{path}[/cyan]")


@guard_app.command("status")
def guard_status_command() -> None:
    """Muestra el estado local de CodeBurn Guard."""
    status = read_guard_status(Path.cwd())
    console.print_json(data=status)
