from __future__ import annotations

from importlib.resources import files as resource_files
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .caveman import DEFAULT_LEVEL, generate_agents_block, upsert_caveman_agents_block, validate_level, write_caveman_skill
from .detect import detect_project
from .doctor import DoctorReport, build_report
from .files import ensure_rtk_excluded, upsert_agents_block, write_text
from .rtk import configure_local_tracking, install_rtk_windows, recommended_commands


app = typer.Typer(
    help="CLI para preparar proyectos con Codex/LLM, RTK y futuras integraciones.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _template(name: str) -> str:
    return resource_files("llm_toolkit").joinpath("templates", name).read_text(encoding="utf-8")


def _print_commands(title: str, commands: list[str] | tuple[str, ...]) -> None:
    console.print(f"[bold]{title}[/bold]")
    for command in commands:
        console.print(f"  [cyan]{command}[/cyan]")


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
    console.print("  No usar para tesis, FEA, simulación, cinemática ni redacción académica.")


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
    _print_caveman_recommendations(report)


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Mostrar la versión y salir."),
) -> None:
    if version:
        console.print(f"llm-toolkit {__version__}")
        raise typer.Exit()


@app.command("init")
def init_command(
    caveman_level_arg: Annotated[
        str | None,
        typer.Argument(help="Nivel Caveman opcional: lite, full o ultra."),
    ] = None,
    rtk: bool = typer.Option(False, "--rtk", help="Inicializar RTK-Codex en el proyecto actual."),
    caveman: bool = typer.Option(False, "--caveman", help="Inicializar Caveman-Codex en el proyecto actual."),
    caveman_level: str | None = typer.Option(
        None,
        "--caveman-level",
        help="Nivel Caveman: lite, full o ultra. Por defecto: lite.",
    ),
) -> None:
    """Inicializa integraciones de llm-toolkit en el directorio actual."""
    if not rtk and not caveman:
        console.print("[yellow]No se indicó integración. Usá --rtk y/o --caveman.[/yellow]")
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

    _print_commands("Comandos recomendados - RTK", recommended_commands(detection.stacks, detection.has_git))


@app.command("doctor")
def doctor_command() -> None:
    """Revisa si el proyecto actual está preparado para RTK-Codex."""
    _print_report(build_report(Path.cwd()))


@app.command("status")
def status_command() -> None:
    """Muestra el estado básico de llm-toolkit en el proyecto actual."""
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
