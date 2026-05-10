from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .caveman import CavemanStatus, get_status as get_caveman_status, recommended_cli_commands, recommended_codex_usage
from .codex_hooks import CodexHookStatus, get_codex_hook_status
from .codeburn import CodeBurnStatus, codeburn_status, recommended_cli_commands as recommended_codeburn_commands
from .detect import ProjectDetection, detect_project
from .files import read_text, skill_has_valid_frontmatter
from .rtk import recommended_commands, rtk_in_path


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    detection: ProjectDetection
    checks: tuple[Check, ...]
    commands: tuple[str, ...]
    caveman: CavemanStatus
    caveman_commands: tuple[str, ...]
    caveman_codex_usage: tuple[str, ...]
    codeburn: CodeBurnStatus
    codeburn_commands: tuple[str, ...]
    codex_hooks: CodexHookStatus

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


def _rtk_excluded(root: Path, has_git: bool) -> bool:
    target = root / ".git" / "info" / "exclude" if has_git else root / ".gitignore"
    return ".rtk/" in read_text(target).splitlines()


def build_report(root: Path | str = ".") -> DoctorReport:
    detection = detect_project(root)
    project_root = detection.root
    agents = project_root / "AGENTS.md"
    skill = project_root / ".agents" / "skills" / "rtk-codex" / "SKILL.md"
    caveman = get_caveman_status(project_root)
    codeburn = codeburn_status(project_root)
    codex_hooks = get_codex_hook_status(project_root)
    checks = (
        Check("rtk en PATH", rtk_in_path(), "rtk disponible" if rtk_in_path() else "rtk no encontrado en PATH"),
        Check("AGENTS.md", agents.exists(), "existe" if agents.exists() else "no existe"),
        Check("skill rtk-codex", skill.exists(), "existe" if skill.exists() else "no existe"),
        Check(
            "frontmatter de skill",
            skill_has_valid_frontmatter(skill),
            "válido" if skill_has_valid_frontmatter(skill) else "inválido o ausente",
        ),
        Check(".rtk/", (project_root / ".rtk").exists(), "existe" if (project_root / ".rtk").exists() else "no existe"),
        Check("exclusión .rtk/", _rtk_excluded(project_root, detection.has_git), "configurada" if _rtk_excluded(project_root, detection.has_git) else "no configurada"),
        Check("Git", detection.has_git, "detectado" if detection.has_git else "no detectado"),
        Check("Caveman configurado", caveman.configured, "sí" if caveman.configured else "no"),
        Check("skill caveman-codex", caveman.skill_exists, "existe" if caveman.skill_exists else "no existe"),
        Check(
            "frontmatter Caveman",
            caveman.skill_frontmatter_valid,
            "válido" if caveman.skill_frontmatter_valid else "inválido o ausente",
        ),
        Check(
            "nivel Caveman",
            caveman.level is not None,
            caveman.level if caveman.level is not None else "no detectado",
        ),
        Check(
            "Node en PATH",
            codeburn.node.found,
            codeburn.node.version or ("detectado" if codeburn.node.found else "no encontrado"),
        ),
        Check(
            "npm en PATH",
            codeburn.npm.found,
            codeburn.npm.version or ("detectado" if codeburn.npm.found else "no encontrado"),
        ),
        Check(
            "codeburn en PATH",
            codeburn.codeburn.found,
            codeburn.codeburn.version or ("detectado" if codeburn.codeburn.found else "no encontrado"),
        ),
        Check(
            "Codex sessions detectadas",
            codeburn.codex_sessions_detected,
            "sí" if codeburn.codex_sessions_detected else "no",
        ),
        Check(
            "bloque CodeBurn en AGENTS.md",
            codeburn.agents_block_configured,
            "configurado" if codeburn.agents_block_configured else "no configurado",
        ),
        Check(
            ".codex/config.toml",
            codex_hooks.config_exists,
            "existe" if codex_hooks.config_exists else "no existe",
        ),
        Check(
            "hooks habilitado",
            codex_hooks.hooks_enabled,
            "true"
            if codex_hooks.hooks_enabled
            else (
                "legacy/deprecated: codex_hooks = true; ejecutar llm-toolkit init --codeburn"
                if codex_hooks.legacy_hooks_enabled
                else "no configurado"
            ),
        ),
        Check(
            ".codex/hooks.json",
            codex_hooks.hooks_json_exists,
            "existe" if codex_hooks.hooks_json_exists else "no existe",
        ),
        Check(
            "guard hook script",
            codex_hooks.hook_script_exists,
            "existe" if codex_hooks.hook_script_exists else "no existe",
        ),
        Check(
            "automatización CodeBurn Guard",
            codex_hooks.automation_ok,
            "configurada" if codex_hooks.automation_ok else "no configurada",
        ),
    )
    return DoctorReport(
        detection=detection,
        checks=checks,
        commands=tuple(recommended_commands(detection.stacks, detection.has_git)),
        caveman=caveman,
        caveman_commands=tuple(recommended_cli_commands(caveman)),
        caveman_codex_usage=tuple(recommended_codex_usage()),
        codeburn=codeburn,
        codeburn_commands=tuple(recommended_codeburn_commands()),
        codex_hooks=codex_hooks,
    )
