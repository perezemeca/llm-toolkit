from pathlib import Path

from llm_toolkit import envcheck


def test_envcheck_detecta_ruta_unica(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(envcheck, "find_all_executable_paths", lambda name: (f"C:\\tools\\{name}.exe",))
    monkeypatch.setattr(envcheck, "_first_line_version", lambda path, args: ("llm-toolkit 0.3.0", None))
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "llm-toolkit"\nversion = "0.3.0"\n', encoding="utf-8")

    report = envcheck.check_environment(tmp_path)

    assert report.level == "OK"
    assert report.active_version == "0.3.0"


def test_envcheck_multiples_rutas_warning(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(envcheck, "find_all_executable_paths", lambda name: ("C:\\a\\llm-toolkit.exe", "C:\\b\\llm-toolkit.exe") if name == "llm-toolkit" else ())
    monkeypatch.setattr(envcheck, "_first_line_version", lambda path, args: ("llm-toolkit 0.3.0", None))
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "llm-toolkit"\nversion = "0.3.0"\n', encoding="utf-8")

    report = envcheck.check_environment(tmp_path)

    assert report.level == "WARNING"
    assert report.multiple_llm_toolkit_paths is True


def test_envcheck_version_distinta_stale(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(envcheck, "find_all_executable_paths", lambda name: ("C:\\tools\\llm-toolkit.exe",) if name == "llm-toolkit" else ())
    monkeypatch.setattr(envcheck, "_first_line_version", lambda path, args: ("llm-toolkit 0.2.0", None))
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "llm-toolkit"\nversion = "0.3.0"\n', encoding="utf-8")

    report = envcheck.check_environment(tmp_path)

    assert report.level == "STALE"
    assert "0.2.0" in report.message


def test_envcheck_no_falla_sin_where(monkeypatch) -> None:
    monkeypatch.setattr(envcheck.shutil, "which", lambda name: None)

    paths = envcheck.find_all_executable_paths("llm-toolkit")

    assert paths == ()
