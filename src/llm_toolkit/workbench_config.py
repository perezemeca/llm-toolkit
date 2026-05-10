from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .caveman import DEFAULT_LEVEL, validate_level
from .files import write_text


CONFIG_DIR_NAME = "llm-toolkit"
CONFIG_FILE_NAME = "workbench.json"
MAX_RECENT_PROJECTS = 10


@dataclass(frozen=True)
class WorkbenchConfig:
    last_project: str | None = None
    recent_projects: tuple[str, ...] = ()
    default_caveman_level: str = DEFAULT_LEVEL
    use_windows_terminal: bool = True
    auto_init: bool = True
    auto_guard: bool = True


def config_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / CONFIG_DIR_NAME
    return Path.home() / "AppData" / "Roaming" / CONFIG_DIR_NAME


def config_path() -> Path:
    return config_dir() / CONFIG_FILE_NAME


def default_config() -> WorkbenchConfig:
    return WorkbenchConfig()


def _normalize_project(path: str | os.PathLike[str]) -> str:
    return str(Path(path).expanduser().resolve())


def _coerce_bool(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _coerce_level(value: object) -> str:
    try:
        return validate_level(str(value))
    except ValueError:
        return DEFAULT_LEVEL


def _coerce_recent(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    recent: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            continue
        try:
            normalized = _normalize_project(item)
        except OSError:
            normalized = item
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        recent.append(normalized)
        if len(recent) >= MAX_RECENT_PROJECTS:
            break
    return tuple(recent)


def load_config(path: Path | None = None) -> WorkbenchConfig:
    target = path or config_path()
    if not target.exists():
        return default_config()
    try:
        data = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default_config()
    if not isinstance(data, dict):
        return default_config()
    last_project = data.get("last_project")
    if not isinstance(last_project, str) or not last_project.strip():
        last_project = None
    return WorkbenchConfig(
        last_project=last_project,
        recent_projects=_coerce_recent(data.get("recent_projects")),
        default_caveman_level=_coerce_level(data.get("default_caveman_level", DEFAULT_LEVEL)),
        use_windows_terminal=_coerce_bool(data.get("use_windows_terminal"), True),
        auto_init=_coerce_bool(data.get("auto_init"), True),
        auto_guard=_coerce_bool(data.get("auto_guard"), True),
    )


def save_config(config: WorkbenchConfig, path: Path | None = None) -> Path:
    target = path or config_path()
    payload = {
        **asdict(config),
        "recent_projects": list(config.recent_projects),
    }
    write_text(target, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return target


def remember_project(config: WorkbenchConfig, project: str | os.PathLike[str]) -> WorkbenchConfig:
    normalized = _normalize_project(project)
    recent = [normalized]
    seen = {normalized.lower()}
    for item in config.recent_projects:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        recent.append(item)
        if len(recent) >= MAX_RECENT_PROJECTS:
            break
    return WorkbenchConfig(
        last_project=normalized,
        recent_projects=tuple(recent),
        default_caveman_level=config.default_caveman_level,
        use_windows_terminal=config.use_windows_terminal,
        auto_init=config.auto_init,
        auto_guard=config.auto_guard,
    )


def update_defaults(
    config: WorkbenchConfig,
    *,
    caveman_level: str | None = None,
    use_windows_terminal: bool | None = None,
    auto_init: bool | None = None,
    auto_guard: bool | None = None,
) -> WorkbenchConfig:
    return WorkbenchConfig(
        last_project=config.last_project,
        recent_projects=config.recent_projects,
        default_caveman_level=_coerce_level(caveman_level or config.default_caveman_level),
        use_windows_terminal=config.use_windows_terminal if use_windows_terminal is None else use_windows_terminal,
        auto_init=config.auto_init if auto_init is None else auto_init,
        auto_guard=config.auto_guard if auto_guard is None else auto_guard,
    )
