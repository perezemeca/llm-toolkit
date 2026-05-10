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


def test_detectar_flutter_por_pubspec_con_sdk_flutter(tmp_path: Path) -> None:
    (tmp_path / "pubspec.yaml").write_text(
        "name: demo\n"
        "dependencies:\n"
        "  flutter:\n"
        "    sdk: flutter\n",
        encoding="utf-8",
    )

    assert detect_stacks(tmp_path) == ("flutter",)


def test_detectar_dart_por_pubspec_sin_flutter(tmp_path: Path) -> None:
    (tmp_path / "pubspec.yaml").write_text(
        "name: demo\n"
        "dependencies:\n"
        "  collection: ^1.18.0\n",
        encoding="utf-8",
    )

    assert detect_stacks(tmp_path) == ("dart",)
