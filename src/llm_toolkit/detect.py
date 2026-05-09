from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


KNOWN_STACKS = ("python", "node", "rust", "go", "dotnet")


@dataclass(frozen=True)
class ProjectDetection:
    root: Path
    has_git: bool
    stacks: tuple[str, ...]

    @property
    def primary_stack(self) -> str:
        return self.stacks[0] if self.stacks else "unknown"


def has_git(root: Path) -> bool:
    return (root / ".git").exists()


def detect_stacks(root: Path) -> tuple[str, ...]:
    stacks: list[str] = []
    if any((root / name).exists() for name in ("pyproject.toml", "requirements.txt", "pytest.ini", ".venv")):
        stacks.append("python")
    if (root / "package.json").exists():
        stacks.append("node")
    if (root / "Cargo.toml").exists():
        stacks.append("rust")
    if (root / "go.mod").exists():
        stacks.append("go")
    if (root / ".sln").exists() or any(root.glob("*.sln")) or any(root.rglob("*.csproj")):
        stacks.append("dotnet")
    return tuple(stacks)


def detect_project(root: Path | str = ".") -> ProjectDetection:
    project_root = Path(root).resolve()
    return ProjectDetection(
        root=project_root,
        has_git=has_git(project_root),
        stacks=detect_stacks(project_root),
    )
