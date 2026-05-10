from __future__ import annotations

import importlib.metadata
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from . import __version__
from .codeburn import SUBPROCESS_TEXT_KWARGS, make_console_safe


EnvLevel = Literal["OK", "WARNING", "STALE"]


@dataclass(frozen=True)
class ExecutableInfo:
    name: str
    active_path: str | None
    paths: tuple[str, ...]
    version: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class EnvReport:
    level: EnvLevel
    message: str
    active_path: str | None
    active_version: str | None
    expected_version: str | None
    origin: str
    multiple_llm_toolkit_paths: bool
    executables: tuple[ExecutableInfo, ...]


def _run(args: list[str], *, timeout: int = 10) -> tuple[int | None, str]:
    try:
        result = subprocess.run(args, check=False, capture_output=True, timeout=timeout, **SUBPROCESS_TEXT_KWARGS)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    output = (result.stdout or result.stderr).strip()
    return result.returncode, make_console_safe(output)


def find_all_executable_paths(name: str) -> tuple[str, ...]:
    paths: list[str] = []
    active = shutil.which(name)
    if active:
        paths.append(active)
    where_path = shutil.which("where.exe")
    if where_path:
        returncode, output = _run([where_path, name], timeout=5)
        if returncode == 0:
            paths.extend(line.strip() for line in output.splitlines() if line.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for path in paths:
        key = path.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(path)
    return tuple(deduped)


def _first_line_version(path: str, args: tuple[str, ...]) -> tuple[str | None, str | None]:
    returncode, output = _run([path, *args], timeout=10)
    if returncode != 0:
        return None, output or f"salió con código {returncode}"
    return output.splitlines()[0].strip() if output else None, None


def detect_executable(name: str, *version_args: str) -> ExecutableInfo:
    paths = find_all_executable_paths(name)
    active = paths[0] if paths else shutil.which(name)
    version = None
    error = None
    if active and version_args:
        version, error = _first_line_version(active, tuple(version_args))
    return ExecutableInfo(name=name, active_path=active, paths=paths, version=version, error=error)


def _read_pyproject_version(root: Path) -> str | None:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        content = pyproject.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    if not re.search(r'(?m)^\s*name\s*=\s*["\']llm-toolkit["\']\s*$', content):
        return None
    match = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']\s*$', content)
    return match.group(1) if match else None


def expected_version(root: Path | str = ".") -> str | None:
    project_root = Path(root)
    pyproject_version = _read_pyproject_version(project_root)
    if pyproject_version:
        return pyproject_version
    try:
        return importlib.metadata.version("llm-toolkit")
    except importlib.metadata.PackageNotFoundError:
        return __version__


def normalize_version(output: str | None) -> str | None:
    if not output:
        return None
    match = re.search(r"(\d+\.\d+\.\d+(?:[A-Za-z0-9.\-+]*)?)", output)
    return match.group(1) if match else output.strip()


def detect_origin(active_path: str | None) -> str:
    if not active_path:
        return "no encontrado"
    normalized = active_path.replace("\\", "/").lower()
    if "/.venv/scripts/" in normalized:
        return ".venv"
    if "/pipx/venvs/" in normalized or "/.local/pipx/venvs/" in normalized:
        return "pipx"
    if "/.local/bin/" in normalized:
        return "global user shim"
    if "/python/scripts/" in normalized:
        return "global user shim"
    if "/programs/python/python" in normalized and "/scripts/" in normalized:
        return "global user shim"
    if "/src/llm_toolkit/" in str(Path(__file__).resolve()).replace("\\", "/").lower():
        repo_root = str(Path(__file__).resolve().parents[2]).replace("\\", "/").lower()
        if normalized.startswith(repo_root):
            return "repo"
    return "desconocido"


def current_process_path() -> str:
    return str(Path(sys.argv[0]).resolve()) if sys.argv and sys.argv[0] else sys.executable


def check_environment(root: Path | str = ".") -> EnvReport:
    llm = detect_executable("llm-toolkit", "--version")
    codex = detect_executable("codex", "--version")
    rtk = detect_executable("rtk", "--version")
    codeburn = detect_executable("codeburn", "--version")
    expected = expected_version(root)
    active_version = normalize_version(llm.version)
    expected_norm = normalize_version(expected)
    multiple = len(llm.paths) > 1

    level: EnvLevel = "OK"
    message = "Env OK"
    if expected_norm and active_version and expected_norm != active_version:
        level = "STALE"
        message = f"Versión activa {active_version} no coincide con versión esperada {expected_norm}."
    elif multiple:
        level = "WARNING"
        message = "Hay múltiples rutas de llm-toolkit resolubles en PATH."
    elif llm.active_path is None:
        level = "WARNING"
        message = "llm-toolkit no se encontró en PATH; usando proceso actual como referencia."

    return EnvReport(
        level=level,
        message=message,
        active_path=llm.active_path or current_process_path(),
        active_version=active_version,
        expected_version=expected_norm,
        origin=detect_origin(llm.active_path),
        multiple_llm_toolkit_paths=multiple,
        executables=(llm, codex, rtk, codeburn),
    )
