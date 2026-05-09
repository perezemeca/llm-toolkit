from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .files import write_text


RTK_WINDOWS_RELEASE_URL = (
    "https://github.com/perezemeca/rtk/releases/latest/download/"
    "rtk-x86_64-pc-windows-msvc.zip"
)


@dataclass(frozen=True)
class RtkConfigResult:
    config_path: Path
    database_path: Path
    backup_path: Path | None


def appdata_dir() -> Path:
    value = os.environ.get("APPDATA")
    if value:
        return Path(value)
    return Path.home() / "AppData" / "Roaming"


def configure_local_tracking(root: Path, appdata: Path | None = None) -> RtkConfigResult:
    rtk_dir = root / ".rtk"
    rtk_dir.mkdir(parents=True, exist_ok=True)
    database_path = rtk_dir / "history.db"
    config_dir = (appdata or appdata_dir()) / "rtk"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"

    backup_path = None
    if config_path.exists():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = config_path.with_suffix(f".toml.bak-{stamp}")
        shutil.copy2(config_path, backup_path)

    db_for_toml = database_path.resolve().as_posix()
    content = (
        "[tracking]\n"
        "enabled = true\n"
        "history_days = 90\n"
        f"database_path = '{db_for_toml}'\n"
    )
    write_text(config_path, content)
    return RtkConfigResult(config_path=config_path, database_path=database_path, backup_path=backup_path)


def recommended_commands(stacks: tuple[str, ...], git_enabled: bool) -> list[str]:
    commands: list[str] = []
    if git_enabled:
        commands.extend(
            [
                "rtk git status",
                "rtk git diff --stat",
                "rtk git diff --name-only",
                "rtk git ls-files",
            ]
        )
    if "python" in stacks:
        commands.extend(
            [
                '$env:Path = "$PWD\\.venv\\Scripts;$env:Path"',
                "rtk pytest -p no:cacheprovider",
            ]
        )
    if "node" in stacks:
        commands.append("rtk npm test")
    if "rust" in stacks:
        commands.append("rtk cargo test")
    if "go" in stacks:
        commands.append("rtk go test ./...")
    if "dotnet" in stacks:
        commands.append("rtk dotnet test")
    commands.append("rtk gain")
    return commands


def rtk_in_path() -> bool:
    return shutil.which("rtk") is not None


def user_local_bin() -> Path:
    return Path.home() / ".local" / "bin"


def path_contains(folder: Path, current_path: str | None = None) -> bool:
    current = current_path if current_path is not None else os.environ.get("PATH", "")
    normalized = str(folder).casefold()
    return any(part.strip().casefold() == normalized for part in current.split(os.pathsep) if part.strip())


def append_user_path_windows(folder: Path) -> None:
    current = os.environ.get("PATH", "")
    if path_contains(folder, current):
        return
    existing_user_path = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "[Environment]::GetEnvironmentVariable('Path', 'User')"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    new_path = str(folder) if not existing_user_path else f"{existing_user_path};{folder}"
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "[Environment]::SetEnvironmentVariable('Path', $args[0], 'User')",
            new_path,
        ],
        check=True,
    )
    os.environ["PATH"] = f"{current}{os.pathsep}{folder}" if current else str(folder)


def install_rtk_windows(release_url: str = RTK_WINDOWS_RELEASE_URL) -> str:
    if not sys.platform.startswith("win"):
        raise RuntimeError("install-rtk solo está implementado para Windows.")

    destination = user_local_bin()
    destination.mkdir(parents=True, exist_ok=True)
    exe_path = destination / "rtk.exe"

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "rtk.zip"
        urllib.request.urlretrieve(release_url, zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            member = next((name for name in archive.namelist() if Path(name).name.lower() == "rtk.exe"), None)
            if member is None:
                raise RuntimeError("El archivo ZIP no contiene rtk.exe.")
            archive.extract(member, tmp)
            extracted = Path(tmp) / member
            shutil.copy2(extracted, exe_path)

    append_user_path_windows(destination)
    result = subprocess.run([str(exe_path), "--version"], check=True, capture_output=True, text=True)
    return result.stdout.strip() or result.stderr.strip()
