from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .files import read_text, skill_has_valid_frontmatter, upsert_marked_block, write_text


CAVEMAN_BEGIN = "<!-- LLM-TOOLKIT:CAVEMAN:BEGIN -->"
CAVEMAN_END = "<!-- LLM-TOOLKIT:CAVEMAN:END -->"
ALLOWED_LEVELS = ("lite", "full", "ultra")
DEFAULT_LEVEL = "lite"


@dataclass(frozen=True)
class CavemanStatus:
    configured: bool
    skill_exists: bool
    skill_frontmatter_valid: bool
    level: str | None


def validate_level(level: str | None) -> str:
    normalized = (level or DEFAULT_LEVEL).strip().lower()
    if normalized not in ALLOWED_LEVELS:
        allowed = ", ".join(ALLOWED_LEVELS)
        raise ValueError(f"Nivel Caveman inválido: {level}. Valores permitidos: {allowed}.")
    return normalized


def generate_agents_block(level: str, template: str) -> str:
    valid_level = validate_level(level)
    return template.replace("{level}", valid_level)


def upsert_caveman_agents_block(root: Path, block_body: str) -> bool:
    path = root / "AGENTS.md"
    before = read_text(path)
    after = upsert_marked_block(before, block_body, CAVEMAN_BEGIN, CAVEMAN_END)
    if before == after:
        return False
    write_text(path, after)
    return True


def write_caveman_skill(root: Path, template: str) -> Path:
    path = root / ".agents" / "skills" / "caveman-codex" / "SKILL.md"
    write_text(path, template)
    return path


def detect_level(root: Path) -> str | None:
    content = read_text(root / "AGENTS.md")
    if CAVEMAN_BEGIN not in content or CAVEMAN_END not in content:
        return None
    _, rest = content.split(CAVEMAN_BEGIN, 1)
    block, _ = rest.split(CAVEMAN_END, 1)
    for line in block.splitlines():
        clean = line.strip().lower()
        if clean.startswith("- nivel configurado:"):
            candidate = clean.split(":", 1)[1].strip(" .`")
            return candidate if candidate in ALLOWED_LEVELS else None
    return None


def get_status(root: Path) -> CavemanStatus:
    agents = read_text(root / "AGENTS.md")
    skill = root / ".agents" / "skills" / "caveman-codex" / "SKILL.md"
    configured = CAVEMAN_BEGIN in agents and CAVEMAN_END in agents
    return CavemanStatus(
        configured=configured,
        skill_exists=skill.exists(),
        skill_frontmatter_valid=skill_has_valid_frontmatter(skill),
        level=detect_level(root),
    )


def recommended_cli_commands(status: CavemanStatus) -> list[str]:
    return [
        "llm-toolkit init --caveman",
        "llm-toolkit init --caveman lite",
        "llm-toolkit init --caveman full",
        "llm-toolkit init --caveman ultra",
        "llm-toolkit init --rtk --caveman lite",
    ]


def recommended_codex_usage() -> list[str]:
    return [
        "$caveman",
        "$caveman lite",
        "$caveman full",
        "$caveman ultra",
    ]
