from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .files import read_text, write_text


CODEX_DIR = ".codex"
CODEX_CONFIG_PATH = Path(CODEX_DIR) / "config.toml"
CODEX_HOOKS_JSON_PATH = Path(CODEX_DIR) / "hooks.json"
CODEX_GUARD_HOOK_PATH = Path(CODEX_DIR) / "hooks" / "llm_toolkit_guard_hook.py"


HOOK_SCRIPT = r'''from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


TEST_COMMAND_RE = re.compile(
    r"(^|\s)(pytest|python\s+-m\s+pytest|npm\s+test|pnpm\s+test|cargo\s+test|dotnet\s+test|go\s+test)(\s|$)",
    re.IGNORECASE,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def state_dir() -> Path:
    return project_root() / ".llm-toolkit"


def log(message: str) -> None:
    path = state_dir() / "logs" / "guard_hook.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{stamp} {message}\n")


def read_payload() -> dict:
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def collect_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        found: list[str] = []
        for item in value.values():
            found.extend(collect_strings(item))
        return found
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(collect_strings(item))
        return found
    return []


def payload_has_test_command(payload: dict) -> bool:
    haystack = "\n".join(collect_strings(payload))
    return bool(TEST_COMMAND_RE.search(haystack))


def write_hook_state(event: str, status: str, detail: str = "") -> None:
    path = state_dir() / "state" / "guard_hook_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "event": event,
        "status": status,
        "detail": detail,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def run_guard_check(timeout: int = 30) -> None:
    env = os.environ.copy()
    executable = shutil.which("llm-toolkit", path=env.get("PATH")) or "llm-toolkit"
    command = [executable, "guard", "check", "--write-alert", "--timeout", str(timeout)]
    try:
        result = subprocess.run(
            command,
            cwd=str(project_root()),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 5,
            env=env,
        )
    except Exception as exc:
        log(f"guard check no bloqueante falló: {exc}")
        write_hook_state("guard_check", "error", str(exc))
        return
    detail = (result.stdout or result.stderr or "").strip().replace("\n", " ")[:500]
    log(f"guard check returncode={result.returncode} {detail}")
    write_hook_state("guard_check", "ok" if result.returncode == 0 else "warning", detail)


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    payload = read_payload()
    try:
        if event in {"session_start", "user_prompt_submit"}:
            run_guard_check()
        elif event == "post_tool_use":
            if payload_has_test_command(payload):
                run_guard_check()
            else:
                write_hook_state(event, "skipped", "sin tanda de tests detectada")
        elif event == "stop":
            write_hook_state(event, "ok", "stop recibido")
        else:
            write_hook_state(event, "ignored", "evento no reconocido")
    except Exception as exc:
        log(f"hook no bloqueante falló en {event}: {exc}")
        write_hook_state(event, "error", str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


@dataclass(frozen=True)
class CodexHookStatus:
    config_exists: bool
    hooks_enabled: bool
    legacy_hooks_enabled: bool
    hooks_json_exists: bool
    hook_script_exists: bool

    @property
    def automation_ok(self) -> bool:
        return (
            self.config_exists
            and (self.hooks_enabled or self.legacy_hooks_enabled)
            and self.hooks_json_exists
            and self.hook_script_exists
        )

    @property
    def migration_needed(self) -> bool:
        return self.legacy_hooks_enabled and not self.hooks_enabled


def _enable_hooks_in_config(content: str) -> str:
    lines = content.splitlines()
    if not lines:
        return "[features]\nhooks = true\n"

    output: list[str] = []
    in_features = False
    saw_features = False
    wrote_key = False

    for line in lines:
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")
        if is_header and in_features and not wrote_key:
            output.append("hooks = true")
            wrote_key = True
        if stripped == "[features]":
            saw_features = True
            in_features = True
            output.append(line)
            continue
        if is_header and stripped != "[features]":
            in_features = False
            output.append(line)
            continue
        if in_features:
            key = stripped.split("=", 1)[0].strip()
            if key in {"hooks", "codex_hooks"}:
                if not wrote_key:
                    output.append("hooks = true")
                    wrote_key = True
                continue
        output.append(line)

    if in_features and not wrote_key:
        output.append("hooks = true")
    if not saw_features:
        if output and output[-1].strip():
            output.append("")
        output.extend(["[features]", "hooks = true"])
    return "\n".join(output).rstrip() + "\n"


def enable_codex_hooks(root: Path | str = ".") -> Path:
    project_root = Path(root)
    path = project_root / CODEX_CONFIG_PATH
    updated = _enable_hooks_in_config(read_text(path))
    write_text(path, updated)
    return path


def build_hooks_config() -> str:
    script = CODEX_GUARD_HOOK_PATH.as_posix()
    hooks = {
        "hooks": {
            "SessionStart": [
                {
                    "command": f"python {script} session_start",
                    "timeout": 35,
                }
            ],
            "UserPromptSubmit": [
                {
                    "command": f"python {script} user_prompt_submit",
                    "timeout": 35,
                }
            ],
            "PostToolUse": [
                {
                    "command": f"python {script} post_tool_use",
                    "timeout": 35,
                }
            ],
            "Stop": [
                {
                    "command": f"python {script} stop",
                    "timeout": 10,
                }
            ],
        }
    }
    return json.dumps(hooks, ensure_ascii=False, indent=2) + "\n"


def write_hooks_json(root: Path | str = ".") -> Path:
    path = Path(root) / CODEX_HOOKS_JSON_PATH
    write_text(path, build_hooks_config())
    return path


def write_guard_hook_script(root: Path | str = ".") -> Path:
    path = Path(root) / CODEX_GUARD_HOOK_PATH
    write_text(path, HOOK_SCRIPT + "\n")
    return path


def install_codex_guard_hooks(root: Path | str = ".") -> CodexHookStatus:
    project_root = Path(root)
    enable_codex_hooks(project_root)
    write_hooks_json(project_root)
    write_guard_hook_script(project_root)
    return get_codex_hook_status(project_root)


def _feature_flags(content: str) -> tuple[bool, bool]:
    hooks_enabled = False
    legacy_hooks_enabled = False
    in_features = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_features = stripped == "[features]"
            continue
        if not in_features or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        enabled = value.split("#", 1)[0].strip().lower() == "true"
        if key.strip() == "hooks":
            hooks_enabled = enabled
        elif key.strip() == "codex_hooks":
            legacy_hooks_enabled = enabled
    return hooks_enabled, legacy_hooks_enabled


def get_codex_hook_status(root: Path | str = ".") -> CodexHookStatus:
    project_root = Path(root)
    config = project_root / CODEX_CONFIG_PATH
    hooks_json = project_root / CODEX_HOOKS_JSON_PATH
    hook_script = project_root / CODEX_GUARD_HOOK_PATH
    config_content = read_text(config)
    hooks_enabled, legacy_hooks_enabled = _feature_flags(config_content) if config.exists() else (False, False)
    return CodexHookStatus(
        config_exists=config.exists(),
        hooks_enabled=hooks_enabled,
        legacy_hooks_enabled=legacy_hooks_enabled,
        hooks_json_exists=hooks_json.exists(),
        hook_script_exists=hook_script.exists(),
    )
