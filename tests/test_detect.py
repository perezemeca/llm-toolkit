from pathlib import Path

from llm_toolkit.detect import detect_project, detect_stacks


def test_detectar_proyecto_sin_git(tmp_path: Path) -> None:
    report = detect_project(tmp_path)

    assert report.has_git is False


def test_detectar_proyecto_con_git(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    report = detect_project(tmp_path)

    assert report.has_git is True


def test_detectar_python_por_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    assert detect_stacks(tmp_path) == ("python",)
