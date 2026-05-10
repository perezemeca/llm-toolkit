from llm_toolkit import envcheck


def test_envcheck_detecta_ruta_unica(monkeypatch) -> None:
    monkeypatch.setattr(envcheck, "find_all_executable_paths", lambda name: (f"C:\\tools\\{name}.exe",))
    monkeypatch.setattr(envcheck, "_first_line_version", lambda path, args: ("llm-toolkit 0.3.0", None))
    monkeypatch.setattr(envcheck, "expected_version", lambda root: "0.3.0")

    report = envcheck.check_environment()

    assert report.level == "OK"
    assert report.active_version == "0.3.0"


def test_envcheck_multiples_rutas_warning(monkeypatch) -> None:
    monkeypatch.setattr(
        envcheck,
        "find_all_executable_paths",
        lambda name: (
            "C:\\Users\\perez\\.local\\bin\\llm-toolkit.EXE",
            "C:\\b\\llm-toolkit.exe",
        )
        if name == "llm-toolkit"
        else (),
    )
    monkeypatch.setattr(envcheck, "_first_line_version", lambda path, args: ("llm-toolkit 0.3.0", None))
    monkeypatch.setattr(envcheck, "expected_version", lambda root: "0.3.0")

    report = envcheck.check_environment()

    assert report.level == "WARNING"
    assert report.multiple_llm_toolkit_paths is True
    assert report.origin == "global user shim"


def test_envcheck_version_distinta_stale(monkeypatch) -> None:
    monkeypatch.setattr(envcheck, "find_all_executable_paths", lambda name: ("C:\\tools\\llm-toolkit.exe",) if name == "llm-toolkit" else ())
    monkeypatch.setattr(envcheck, "_first_line_version", lambda path, args: ("llm-toolkit 0.2.0", None))
    monkeypatch.setattr(envcheck, "expected_version", lambda root: "0.3.0")

    report = envcheck.check_environment()

    assert report.level == "STALE"
    assert "0.2.0" in report.message


def test_envcheck_no_falla_sin_where(monkeypatch) -> None:
    monkeypatch.setattr(envcheck.shutil, "which", lambda name: None)

    paths = envcheck.find_all_executable_paths("llm-toolkit")

    assert paths == ()


def test_detect_origin_venv_scripts() -> None:
    assert envcheck.detect_origin("C:\\repo\\.venv\\Scripts\\llm-toolkit.exe") == ".venv"


def test_detect_origin_pipx_venv() -> None:
    assert envcheck.detect_origin("C:\\Users\\perez\\pipx\\venvs\\llm-toolkit\\Scripts\\llm-toolkit.exe") == "pipx"


def test_detect_origin_global_user_shim_local_bin() -> None:
    assert envcheck.detect_origin("C:\\Users\\perez\\.local\\bin\\llm-toolkit.EXE") == "global user shim"


def test_detect_origin_desconocido() -> None:
    assert envcheck.detect_origin("C:\\tools\\llm-toolkit.exe") == "desconocido"
