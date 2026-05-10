from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .envcheck import EnvReport, check_environment
from .files import read_text, write_text


StaleLevel = Literal["OK", "WARNING", "STALE"]
FINGERPRINT_PATH = Path(".llm-toolkit") / "state" / "session_fingerprint.json"


@dataclass(frozen=True)
class FileFingerprint:
    sha256: str
    mtime_ns: int
    size: int


@dataclass(frozen=True)
class SessionFingerprint:
    marked_at: str
    files: dict[str, FileFingerprint]
    llm_toolkit_version: str | None
    llm_toolkit_path: str | None
    codex_version: str | None
    shell_pid: int


@dataclass(frozen=True)
class StaleReport:
    level: StaleLevel
    message: str
    changed_files: tuple[str, ...]
    env_level: str
    env_message: str
    fingerprint_path: str
    recommendation: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_llm_toolkit_repo(root: Path) -> bool:
    pyproject = root / "pyproject.toml"
    return pyproject.exists() and 'name = "llm-toolkit"' in read_text(pyproject)


def sensitive_files(root: Path) -> tuple[Path, ...]:
    candidates: list[Path] = [
        root / ".codex" / "config.toml",
        root / ".codex" / "hooks.json",
        root / ".codex" / "hooks" / "llm_toolkit_guard_hook.py",
        root / "AGENTS.md",
    ]
    skills = root / ".agents" / "skills"
    if skills.exists():
        candidates.extend(sorted(skills.glob("**/*.md")))
    if _is_llm_toolkit_repo(root):
        candidates.extend(sorted((root / "src" / "llm_toolkit").glob("**/*.py")))
    return tuple(path for path in candidates if path.exists())


def _hash_file(path: Path) -> FileFingerprint:
    data = path.read_bytes()
    stat = path.stat()
    return FileFingerprint(sha256=hashlib.sha256(data).hexdigest(), mtime_ns=stat.st_mtime_ns, size=stat.st_size)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def build_fingerprint(root: Path | str = ".", env: EnvReport | None = None) -> SessionFingerprint:
    project_root = Path(root)
    env_report = env or check_environment(project_root)
    codex_version = None
    for executable in env_report.executables:
        if executable.name == "codex":
            codex_version = executable.version
            break
    files = {_relative(path, project_root): _hash_file(path) for path in sensitive_files(project_root)}
    return SessionFingerprint(
        marked_at=utc_now(),
        files=files,
        llm_toolkit_version=env_report.active_version,
        llm_toolkit_path=env_report.active_path,
        codex_version=codex_version,
        shell_pid=os.getpid(),
    )


def _fingerprint_to_json(fingerprint: SessionFingerprint) -> str:
    return json.dumps(asdict(fingerprint), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _file_fingerprint_from_dict(data: dict) -> FileFingerprint:
    return FileFingerprint(sha256=str(data["sha256"]), mtime_ns=int(data["mtime_ns"]), size=int(data["size"]))


def _fingerprint_from_json(content: str) -> SessionFingerprint | None:
    try:
        data = json.loads(content)
        return SessionFingerprint(
            marked_at=str(data["marked_at"]),
            files={str(k): _file_fingerprint_from_dict(v) for k, v in dict(data["files"]).items()},
            llm_toolkit_version=data.get("llm_toolkit_version"),
            llm_toolkit_path=data.get("llm_toolkit_path"),
            codex_version=data.get("codex_version"),
            shell_pid=int(data.get("shell_pid") or 0),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def mark_clean(root: Path | str = ".") -> Path:
    project_root = Path(root)
    path = project_root / FINGERPRINT_PATH
    write_text(path, _fingerprint_to_json(build_fingerprint(project_root)))
    return path


def load_fingerprint(root: Path | str = ".") -> SessionFingerprint | None:
    path = Path(root) / FINGERPRINT_PATH
    content = read_text(path)
    return _fingerprint_from_json(content) if content else None


def check_stale(root: Path | str = ".") -> StaleReport:
    project_root = Path(root)
    env_report = check_environment(project_root)
    path = project_root / FINGERPRINT_PATH
    previous = load_fingerprint(project_root)
    if previous is None:
        return StaleReport(
            level="WARNING",
            message="No hay fingerprint de sesión marcado.",
            changed_files=(),
            env_level=env_report.level,
            env_message=env_report.message,
            fingerprint_path=str(path),
            recommendation="Ejecutar `llm-toolkit stale mark-clean` después de reiniciar Codex/PowerShell.",
        )

    current = build_fingerprint(project_root, env_report)
    changed: list[str] = []
    for rel_path, fingerprint in current.files.items():
        if previous.files.get(rel_path) != fingerprint:
            changed.append(rel_path)
    for rel_path in previous.files:
        if rel_path not in current.files:
            changed.append(rel_path)

    env_changed = (
        previous.llm_toolkit_path != current.llm_toolkit_path
        or previous.llm_toolkit_version != current.llm_toolkit_version
        or previous.codex_version != current.codex_version
    )
    if env_report.level == "STALE" or changed or env_changed:
        recommendation = "Reiniciar Codex si cambiaron .codex/, AGENTS.md o skills; reiniciar PowerShell si cambió PATH o versión."
        if env_changed or env_report.level == "STALE":
            recommendation = "La terminal puede estar usando una versión vieja. Reiniciar PowerShell o validar con `where.exe llm-toolkit`."
        return StaleReport(
            level="STALE",
            message="Configuración, hooks o versión activa cambiaron desde el último fingerprint.",
            changed_files=tuple(sorted(set(changed))),
            env_level=env_report.level,
            env_message=env_report.message,
            fingerprint_path=str(path),
            recommendation=recommendation,
        )

    return StaleReport(
        level="OK",
        message="Sin cambios sensibles desde el último fingerprint.",
        changed_files=(),
        env_level=env_report.level,
        env_message=env_report.message,
        fingerprint_path=str(path),
        recommendation=None,
    )
