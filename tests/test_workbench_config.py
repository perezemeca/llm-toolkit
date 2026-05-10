from pathlib import Path

from llm_toolkit.workbench_config import (
    WorkbenchConfig,
    load_config,
    remember_project,
    save_config,
    update_defaults,
)


def test_workbench_config_read_write(tmp_path: Path) -> None:
    path = tmp_path / "workbench.json"
    config = WorkbenchConfig(
        last_project="C:\\repo",
        recent_projects=("C:\\repo",),
        default_caveman_level="full",
        use_windows_terminal=False,
        auto_init=False,
        auto_guard=False,
    )

    save_config(config, path)
    loaded = load_config(path)

    assert loaded == config


def test_workbench_config_defaults_if_file_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.json")

    assert config.default_caveman_level == "lite"
    assert config.use_windows_terminal is True
    assert config.auto_init is True
    assert config.auto_guard is True


def test_remember_project_dedupes_and_moves_to_front(tmp_path: Path) -> None:
    first = tmp_path / "Proyecto Uno"
    second = tmp_path / "Proyecto Dos"
    first.mkdir()
    second.mkdir()
    config = WorkbenchConfig(recent_projects=(str(first), str(second)))

    updated = remember_project(config, second)

    assert updated.last_project == str(second.resolve())
    assert updated.recent_projects[0] == str(second.resolve())
    assert updated.recent_projects[1] == str(first.resolve())
    assert len(updated.recent_projects) == 2


def test_update_defaults_sanea_nivel_invalido() -> None:
    config = update_defaults(WorkbenchConfig(), caveman_level="nope")

    assert config.default_caveman_level == "lite"
