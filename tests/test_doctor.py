from pathlib import Path

from llm_toolkit.doctor import build_report
from llm_toolkit.files import ensure_rtk_excluded, write_text


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
