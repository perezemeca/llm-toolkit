from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


TEST_COMMAND_RE = re.compile(
    r"(^|\s)(pytest|python\s+-m\s+pytest|npm\s+test|pnpm\s+test|cargo\s+test|dotnet\s+test|go\s+test|flutter\s+test|dart\s+test|flutter\s+analyze|dart\s+analyze)(\s|$)",
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

