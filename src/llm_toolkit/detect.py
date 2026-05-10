from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


KNOWN_STACKS = ("python", "node", "rust", "go", "dotnet", "flutter", "dart")


FLUTTER_PROJECT_DIRS = ("android", "ios", "macos", "web", "windows", "linux")


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


def has_pubspec(root: Path) -> bool:
    return (root / "pubspec.yaml").exists()


def _pubspec_text(root: Path) -> str:
    path = root / "pubspec.yaml"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _pubspec_mentions_flutter(content: str) -> bool:
    normalized = content.lower()
    return "sdk: flutter" in normalized or "\n  flutter:" in normalized or "\nflutter:" in normalized


def _has_flutter_structure(root: Path) -> bool:
    return (root / "lib" / "main.dart").exists() and any((root / name).exists() for name in FLUTTER_PROJECT_DIRS)


def detect_flutter(root: Path) -> bool:
    if not has_pubspec(root):
        return False
    return _pubspec_mentions_flutter(_pubspec_text(root)) or _has_flutter_structure(root)


def detect_dart(root: Path) -> bool:
    return has_pubspec(root) and not detect_flutter(root)


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
    if detect_flutter(root):
        stacks.append("flutter")
    elif detect_dart(root):
        stacks.append("dart")
    return tuple(stacks)


def detect_project(root: Path | str = ".") -> ProjectDetection:
    project_root = Path(root).resolve()
    return ProjectDetection(
        root=project_root,
        has_git=has_git(project_root),
        stacks=detect_stacks(project_root),
    )
