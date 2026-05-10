from pathlib import Path

from llm_toolkit.envcheck import EnvReport, ExecutableInfo
from llm_toolkit import stale


def fake_env(path: str = "C:\\tools\\llm-toolkit.exe", version: str = "0.3.0") -> EnvReport:
    return EnvReport(
        level="OK",
        message="Env OK",
        active_path=path,
        active_version=version,
        expected_version="0.3.0",
        origin="pipx",
        multiple_llm_toolkit_paths=False,
        executables=(ExecutableInfo("codex", "C:\\tools\\codex.exe", ("C:\\tools\\codex.exe",), "codex 0.130.0"),),
    )


def test_stale_mark_clean_crea_fingerprint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(stale, "check_environment", lambda root: fake_env())
    (tmp_path / "AGENTS.md").write_text("demo\n", encoding="utf-8")

    path = stale.mark_clean(tmp_path)

    assert path.exists()
    assert "AGENTS.md" in path.read_text(encoding="utf-8")


def test_stale_check_ok_si_nada_cambio(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(stale, "check_environment", lambda root: fake_env())
    (tmp_path / "AGENTS.md").write_text("demo\n", encoding="utf-8")
    stale.mark_clean(tmp_path)

    report = stale.check_stale(tmp_path)

    assert report.level == "OK"


def test_stale_check_stale_si_cambia_agents(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(stale, "check_environment", lambda root: fake_env())
    (tmp_path / "AGENTS.md").write_text("demo\n", encoding="utf-8")
    stale.mark_clean(tmp_path)
    (tmp_path / "AGENTS.md").write_text("demo cambiado\n", encoding="utf-8")

    report = stale.check_stale(tmp_path)

    assert report.level == "STALE"
    assert "AGENTS.md" in report.changed_files


def test_stale_check_stale_si_cambia_hooks_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(stale, "check_environment", lambda root: fake_env())
    hooks = tmp_path / ".codex" / "hooks.json"
    hooks.parent.mkdir(parents=True)
    hooks.write_text("{}\n", encoding="utf-8")
    stale.mark_clean(tmp_path)
    hooks.write_text('{"hooks": {}}\n', encoding="utf-8")

    report = stale.check_stale(tmp_path)

    assert report.level == "STALE"
    assert ".codex/hooks.json" in report.changed_files


def test_stale_check_stale_si_cambia_version_o_ruta(tmp_path: Path, monkeypatch) -> None:
    values = [fake_env(path="C:\\a\\llm-toolkit.exe"), fake_env(path="C:\\b\\llm-toolkit.exe")]
    monkeypatch.setattr(stale, "check_environment", lambda root: values.pop(0))
    (tmp_path / "AGENTS.md").write_text("demo\n", encoding="utf-8")
    stale.mark_clean(tmp_path)

    report = stale.check_stale(tmp_path)

    assert report.level == "STALE"
    assert "versión vieja" in (report.recommendation or "")


def test_stale_no_falla_sin_fingerprint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(stale, "check_environment", lambda root: fake_env())

    report = stale.check_stale(tmp_path)

    assert report.level == "WARNING"
