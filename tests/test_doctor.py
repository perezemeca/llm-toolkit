from pathlib import Path

from typer.testing import CliRunner

from llm_toolkit import doctor
from llm_toolkit.cli import app
from llm_toolkit.doctor import build_report
from llm_toolkit.files import ensure_rtk_excluded, write_text
from llm_toolkit.rtk import recommended_commands


runner = CliRunner()


def test_doctor_reporta_estado_basico_sin_fallar(tmp_path: Path) -> None:
    (tmp_path / ".git" / "info").mkdir(parents=True)
    (tmp_path / ".rtk").mkdir()
    (tmp_path / "AGENTS.md").write_text("Demo\n", encoding="utf-8")
    write_text(
        tmp_path / ".agents" / "skills" / "rtk-codex" / "SKILL.md",
        "---\nname: rtk-codex\ndescription: Demo\n---\n\nContenido\n",
    )
    ensure_rtk_excluded(tmp_path, git_enabled=True)

    report = build_report(tmp_path)

    assert report.detection.has_git is True
    assert any(check.name == "AGENTS.md" and check.ok for check in report.checks)
    assert any(command == "rtk gain" for command in report.commands)


def test_doctor_status_no_fallan_sin_flutter_ni_dart_en_path(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pubspec.yaml").write_text("name: demo\n", encoding="utf-8")
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    monkeypatch.chdir(tmp_path)

    report = build_report(tmp_path)
    status = runner.invoke(app, ["status"])

    assert report.detection.stacks == ("dart",)
    assert any(check.name == "Flutter en PATH" and not check.ok for check in report.checks)
    assert any(check.name == "Dart en PATH" and not check.ok for check in report.checks)
    assert any(check.name == "pubspec.yaml" and check.ok for check in report.checks)
    assert status.exit_code == 0
    assert "Stack: dart" in status.output
    assert "Flutter en PATH" in status.output
    assert "Dart en PATH" in status.output


def test_comandos_recomendados_incluyen_flutter_y_dart() -> None:
    flutter_commands = recommended_commands(("flutter",), git_enabled=False)
    dart_commands = recommended_commands(("dart",), git_enabled=False)

    assert "rtk flutter pub get" in flutter_commands
    assert "rtk flutter analyze" in flutter_commands
    assert "rtk flutter test" in flutter_commands
    assert "flutter test --reporter compact" in flutter_commands
    assert "flutter analyze --no-pub" in flutter_commands
    assert "rtk dart pub get" in dart_commands
    assert "rtk dart analyze" in dart_commands
    assert "rtk dart test" in dart_commands
    assert "dart test --reporter compact" in dart_commands
