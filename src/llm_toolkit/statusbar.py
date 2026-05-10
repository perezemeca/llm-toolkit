from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .codeburn import SUBPROCESS_TEXT_KWARGS, make_console_safe
from .envcheck import check_environment
from .files import read_text
from .stale import check_stale


@dataclass(frozen=True)
class ContextUsage:
    percent: float | None
    input_tokens: int | None
    context_window: int | None
    source_path: str | None

    @property
    def level(self) -> str:
        if self.percent is None:
            return "UNKNOWN"
        if self.percent >= 85:
            return "CRITICAL"
        if self.percent >= 70:
            return "WARNING"
        return "OK"


def _codex_sessions_root(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".codex" / "sessions"


def latest_session_files(home: Path | None = None) -> list[Path]:
    root = _codex_sessions_root(home)
    if not root.exists():
        return []
    try:
        files = [path for path in root.rglob("rollout-*.jsonl") if path.is_file() and path.stat().st_size > 0]
    except OSError:
        return []
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def parse_context_usage_from_jsonl(path: Path) -> ContextUsage | None:
    last_info: dict | None = None
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if '"type":"token_count"' not in line and '"type": "token_count"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") or {}
                if payload.get("type") != "token_count":
                    continue
                info = payload.get("info")
                if isinstance(info, dict):
                    last_info = info
    except OSError:
        return None
    if not last_info:
        return None
    usage = last_info.get("last_token_usage") or {}
    context_window = last_info.get("model_context_window")
    input_tokens = usage.get("input_tokens")
    if not isinstance(input_tokens, int) or not isinstance(context_window, int) or context_window <= 0:
        return None
    return ContextUsage(
        percent=(input_tokens / context_window) * 100,
        input_tokens=input_tokens,
        context_window=context_window,
        source_path=str(path),
    )


def read_latest_context_usage(home: Path | None = None) -> ContextUsage:
    for path in latest_session_files(home):
        usage = parse_context_usage_from_jsonl(path)
        if usage is not None:
            return usage
    return ContextUsage(percent=None, input_tokens=None, context_window=None, source_path=None)


def _read_guard_level(root: Path) -> str:
    state = root / ".llm-toolkit" / "state" / "context_health.json"
    if not state.exists():
        return "OK"
    try:
        data = json.loads(read_text(state))
    except json.JSONDecodeError:
        return "UNKNOWN"
    level = data.get("level")
    return str(level) if level else "UNKNOWN"


def _has_alert(root: Path) -> bool:
    return (root / ".llm-toolkit" / "alerts" / "CODEX_ALERT.md").exists()


def _rtk_gain_summary(timeout: int = 3) -> str | None:
    try:
        result = subprocess.run(["rtk", "gain"], check=False, capture_output=True, timeout=timeout, **SUBPROCESS_TEXT_KWARGS)
    except (OSError, subprocess.SubprocessError):
        return None
    output = make_console_safe((result.stdout or result.stderr).strip())
    if result.returncode != 0:
        return None
    saved = re.search(r"Tokens saved:\s+([^\n]+)", output)
    return f"RTK {saved.group(1).strip()}" if saved else None


def build_statusbar_line(root: Path | str = ".", *, include_rtk: bool = True, home: Path | None = None) -> str:
    project_root = Path(root)
    usage = read_latest_context_usage(home)
    ctx = "CTX n/d" if usage.percent is None else f"CTX {usage.percent:.1f}% est"
    ctx_level = usage.level if usage.level != "UNKNOWN" else "n/d"
    guard = _read_guard_level(project_root)
    env = check_environment(project_root)
    stale = check_stale(project_root)
    env_level = "STALE" if stale.level == "STALE" or env.level == "STALE" else env.level
    parts = [ctx, ctx_level, f"Guard {guard}", f"Env {env_level}"]
    if _has_alert(project_root):
        parts.append("Alert sí")
    if include_rtk:
        rtk = _rtk_gain_summary()
        if rtk:
            parts.append(rtk)
    return " | ".join(parts)
