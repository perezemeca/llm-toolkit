from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    )
    return DoctorReport(
        detection=detection,
        checks=checks,
        commands=tuple(recommended_commands(detection.stacks, detection.has_git)),
    )
