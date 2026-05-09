from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .codeburn import SUBPROCESS_TEXT_KWARGS, detect_codeburn, make_console_safe
from .files import append_unique_line, write_text


GuardLevel = Literal["HEALTHY", "UNKNOWN", "WARNING", "CRITICAL"]

STATE_DIR = ".llm-toolkit"
CONTEXT_HEALTH_PATH = Path(STATE_DIR) / "state" / "context_health.json"
ALERT_PATH = Path(STATE_DIR) / "alerts" / "CODEX_ALERT.md"
GUARD_STATUS_PATH = Path(STATE_DIR) / "state" / "guard_status.json"


@dataclass(frozen=True)
class GuardResult:
    level: GuardLevel
    message: str
    codeburn_available: bool
    returncode: int | None
    checked_at: str
    summary: str
    alert_path: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_guard_excluded(root: Path | str = ".") -> Path:
    path = Path(root) / ".gitignore"
    append_unique_line(path, f"{STATE_DIR}/")
    return path


def run_codeburn_optimize(timeout: int = 30) -> tuple[bool, int | None, str]:
    codeburn = detect_codeburn()
    if not codeburn.found:
        return False, None, "CodeBurn no está instalado. El guard no bloquea la tarea."
    try:
        result = subprocess.run(
            [codeburn.path or "codeburn", "optimize"],
            check=False,
            capture_output=True,
            timeout=timeout,
            **SUBPROCESS_TEXT_KWARGS,
        )
    except subprocess.TimeoutExpired:
        return True, None, f"CodeBurn optimize superó el timeout de {timeout}s. El guard no bloquea la tarea."
    except (OSError, subprocess.SubprocessError) as exc:
        return True, None, f"CodeBurn optimize falló: {exc}. El guard no bloquea la tarea."
    output = make_console_safe((result.stdout or result.stderr).strip())
    return True, result.returncode, output


def classify_codeburn_output(output: str, codeburn_available: bool, returncode: int | None) -> tuple[GuardLevel, str]:
    if not codeburn_available:
        return "UNKNOWN", "CodeBurn no está instalado."
    if returncode not in (0, None) and not output.strip():
        return "UNKNOWN", "CodeBurn no devolvió datos locales de sesiones."
    normalized = output.lower()
    if not normalized.strip():
        return "UNKNOWN", "CodeBurn no devolvió datos locales de sesiones."

    has_context_heavy = "context-heavy sessions" in normalized
    has_potential_savings = "potential savings" in normalized and not re.search(r"potential savings:\s*(0|~0)(\D|$)", normalized)
    ratios = [float(match.group(1)) for match in re.finditer(r"\((\d+(?:\.\d+)?):1(?:,|\))", output)]
    high_ratio = any(ratio >= 30 for ratio in ratios)
    high_severity = bool(re.search(r"\bhigh\b", normalized))

    if has_context_heavy and (high_severity or high_ratio):
        return "CRITICAL", "CodeBurn detectó sesiones context-heavy con severidad High o ratio input/output alto."
    if has_context_heavy or has_potential_savings:
        return "WARNING", "CodeBurn detectó contexto pesado o ahorro potencial relevante."
    return "HEALTHY", "No se detectaron señales de contexto pesado."


def build_context_health(result: GuardResult) -> str:
    return json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n"


def build_alert(result: GuardResult) -> str:
    return (
        "# CODEX ALERT\n\n"
        f"Estado: {result.level}\n\n"
        f"Chequeado: {result.checked_at}\n\n"
        f"{result.message}\n\n"
        "Regla de contexto fresco:\n\n"
        "- Iniciar un hilo nuevo o limpiar contexto si la tarea sigue siendo pesada.\n"
        "- Usar solo el objetivo actual, archivos relevantes, salida fallida y restricciones vigentes.\n"
        "- Restatar el contexto de trabajo en menos de 10 bullets antes de editar.\n"
        "- No bloquear tareas funcionales si CodeBurn falla o no tiene datos.\n\n"
        "Resumen CodeBurn:\n\n"
        "```text\n"
        f"{result.summary.strip() or 'Sin datos locales.'}\n"
        "```\n"
    )


def write_context_health(root: Path, result: GuardResult) -> Path:
    path = root / CONTEXT_HEALTH_PATH
    write_text(path, build_context_health(result))
    return path


def write_alert(root: Path, result: GuardResult) -> Path | None:
    if result.level not in ("WARNING", "CRITICAL"):
        return None
    path = root / ALERT_PATH
    write_text(path, build_alert(result))
    return path


def check_guard(root: Path | str = ".", *, timeout: int = 30, write_alert_file: bool = False) -> GuardResult:
    project_root = Path(root)
    ensure_guard_excluded(project_root)
    codeburn_available, returncode, output = run_codeburn_optimize(timeout=timeout)
    level, message = classify_codeburn_output(output, codeburn_available, returncode)
    result = GuardResult(
        level=level,
        message=message,
        codeburn_available=codeburn_available,
        returncode=returncode,
        checked_at=utc_now(),
        summary=output,
    )
    write_context_health(project_root, result)
    alert = write_alert(project_root, result) if write_alert_file else None
    if alert is not None:
        result = GuardResult(**{**asdict(result), "alert_path": str(alert)})
        write_context_health(project_root, result)
    return result


def start_guard(root: Path | str = ".", *, interval: int = 300, timeout: int = 30) -> Path:
    project_root = Path(root)
    ensure_guard_excluded(project_root)
    payload = {
        "active": True,
        "interval": interval,
        "timeout": timeout,
        "started_at": utc_now(),
        "mode": "checkpoint",
        "note": "No inicia un proceso residente; registra la política para checkpoints de Codex.",
    }
    path = project_root / GUARD_STATUS_PATH
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def stop_guard(root: Path | str = ".") -> Path:
    project_root = Path(root)
    ensure_guard_excluded(project_root)
    path = project_root / GUARD_STATUS_PATH
    payload = {
        "active": False,
        "stopped_at": utc_now(),
        "mode": "checkpoint",
    }
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def read_guard_status(root: Path | str = ".") -> dict[str, object]:
    path = Path(root) / GUARD_STATUS_PATH
    if not path.exists():
        return {"active": False, "mode": "checkpoint", "detail": "Guard no iniciado."}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"active": False, "mode": "checkpoint", "detail": "Estado de guard inválido."}
