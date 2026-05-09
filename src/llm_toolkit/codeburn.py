from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from importlib.resources import files as resource_files
from pathlib import Path

from .codex_hooks import install_codex_guard_hooks
from .files import read_text, upsert_marked_block, write_text


CODEBURN_BEGIN = "<!-- LLM-TOOLKIT:CODEBURN:BEGIN -->"
CODEBURN_END = "<!-- LLM-TOOLKIT:CODEBURN:END -->"
SUBPROCESS_TEXT_KWARGS = {
    "text": True,
    "encoding": "utf-8",
    "errors": "replace",
}
BOX_DRAWING_TRANSLATION = str.maketrans(
    {
        "─": "-",
        "━": "-",
        "│": "|",
        "┃": "|",
        "┌": "+",
        "┐": "+",
        "└": "+",
        "┘": "+",
        "├": "+",
        "┤": "+",
        "┬": "+",
        "┴": "+",
        "┼": "+",
        "╭": "+",
        "╮": "+",
        "╰": "+",
        "╯": "+",
        "═": "=",
        "║": "|",
        "╔": "+",
        "╗": "+",
        "╚": "+",
        "╝": "+",
        "╠": "+",
        "╣": "+",
        "╦": "+",
        "╩": "+",
        "╬": "+",
        "→": "->",
        "←": "<-",
        "≈": "~",
    }
)


@dataclass(frozen=True)
class ExecutableStatus:
    found: bool
    path: str | None = None
    version: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class CodeBurnStatus:
    node: ExecutableStatus
    npm: ExecutableStatus
    codeburn: ExecutableStatus
    codex_sessions_detected: bool
    agents_block_configured: bool


@dataclass(frozen=True)
class CodeBurnCommandResult:
    returncode: int
    stdout: str
    stderr: str
    executable_found: bool


def make_console_safe(text: str) -> str:
    return text.translate(BOX_DRAWING_TRANSLATION)


def _run_version(path: str, *args: str) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            [path, *args],
            check=False,
            capture_output=True,
            timeout=15,
            **SUBPROCESS_TEXT_KWARGS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    output = (result.stdout or result.stderr).strip()
    output = make_console_safe(output)
    if result.returncode != 0:
        return None, output or f"salió con código {result.returncode}"
    first_line = output.splitlines()[0].strip() if output else None
    return first_line, None


def _detect_executable(name: str, *version_args: str) -> ExecutableStatus:
    path = shutil.which(name)
    if path is None:
        return ExecutableStatus(found=False, error=f"{name} no encontrado en PATH")
    version, error = _run_version(path, *version_args)
    return ExecutableStatus(found=True, path=path, version=version, error=error)


def detect_node() -> ExecutableStatus:
    return _detect_executable("node", "--version")


def detect_npm() -> ExecutableStatus:
    return _detect_executable("npm", "--version")


def detect_codeburn() -> ExecutableStatus:
    status = _detect_executable("codeburn", "--version")
    if status.found and status.version is None:
        version, error = _run_version(status.path or "codeburn", "status")
        return ExecutableStatus(found=True, path=status.path, version=version, error=error)
    return status


def detect_codex_sessions(home: Path | None = None) -> bool:
    base = home or Path.home()
    candidates = (
        base / ".codex" / "sessions",
        base / ".codex" / "projects",
    )
    for candidate in candidates:
        try:
            if candidate.exists() and any(candidate.rglob("*")):
                return True
        except OSError:
            continue
    return False


def install_codeburn_windows() -> ExecutableStatus:
    node = detect_node()
    if not node.found:
        raise RuntimeError("Node no está instalado o no está en PATH. Instalá Node.js y volvé a ejecutar.")
    npm = detect_npm()
    if not npm.found:
        raise RuntimeError("npm no está instalado o no está en PATH. Instalá npm y volvé a ejecutar.")

    npm_path = npm.path or "npm"
    result = subprocess.run(
        [npm_path, "install", "-g", "codeburn"],
        check=False,
        capture_output=True,
        timeout=600,
        **SUBPROCESS_TEXT_KWARGS,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        detail = make_console_safe(detail)
        raise RuntimeError(f"No se pudo instalar CodeBurn: {detail}")

    codeburn = detect_codeburn()
    if not codeburn.found:
        raise RuntimeError("npm finalizó, pero codeburn no quedó disponible en PATH.")
    return codeburn


def build_codeburn_agents_block() -> str:
    return resource_files("llm_toolkit").joinpath("templates", "AGENTS_CODEBURN_BLOCK.md").read_text(encoding="utf-8")


def create_or_update_codeburn_integration(root: Path | str = ".") -> bool:
    project_root = Path(root)
    path = project_root / "AGENTS.md"
    before = read_text(path)
    after = upsert_marked_block(before, build_codeburn_agents_block(), CODEBURN_BEGIN, CODEBURN_END)
    install_codex_guard_hooks(project_root)
    if before == after:
        return False
    write_text(path, after)
    return True


def codeburn_status(root: Path | str = ".") -> CodeBurnStatus:
    project_root = Path(root)
    agents = read_text(project_root / "AGENTS.md")
    return CodeBurnStatus(
        node=detect_node(),
        npm=detect_npm(),
        codeburn=detect_codeburn(),
        codex_sessions_detected=detect_codex_sessions(),
        agents_block_configured=CODEBURN_BEGIN in agents and CODEBURN_END in agents,
    )


def recommended_cli_commands() -> list[str]:
    return [
        "llm-toolkit install-codeburn",
        "llm-toolkit init --codeburn",
        "llm-toolkit metrics",
        "llm-toolkit metrics --today",
        "llm-toolkit metrics --month",
        "llm-toolkit metrics --json",
        "llm-toolkit optimize",
        "llm-toolkit guard check --write-alert",
        "llm-toolkit guard start --interval 300 --timeout 30",
        "llm-toolkit guard status",
        "llm-toolkit guard stop",
    ]


def run_codeburn_command(args: list[str]) -> CodeBurnCommandResult:
    codeburn = detect_codeburn()
    if not codeburn.found:
        return CodeBurnCommandResult(
            returncode=127,
            stdout="",
            stderr="CodeBurn no está instalado. Ejecutar llm-toolkit install-codeburn.",
            executable_found=False,
        )
    try:
        result = subprocess.run(
            [codeburn.path or "codeburn", *args],
            check=False,
            capture_output=True,
            timeout=120,
            **SUBPROCESS_TEXT_KWARGS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CodeBurnCommandResult(returncode=1, stdout="", stderr=str(exc), executable_found=True)
    return CodeBurnCommandResult(
        returncode=result.returncode,
        stdout=make_console_safe(result.stdout),
        stderr=make_console_safe(result.stderr),
        executable_found=True,
    )
