import json
from pathlib import Path

from llm_toolkit import statusbar
from llm_toolkit.envcheck import EnvReport
from llm_toolkit.stale import StaleReport


def write_session(path: Path, input_tokens: int, total_tokens: int = 999999, context_window: int = 100000) -> None:
    path.parent.mkdir(parents=True)
    event = {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {"input_tokens": total_tokens, "total_tokens": total_tokens},
                "last_token_usage": {"input_tokens": input_tokens, "total_tokens": input_tokens + 100},
                "model_context_window": context_window,
            },
        },
    }
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")


def test_statusbar_parsea_token_count_y_calcula_decimal(tmp_path: Path) -> None:
    session = tmp_path / ".codex" / "sessions" / "2026" / "05" / "10" / "rollout-demo.jsonl"
    write_session(session, 73900, context_window=100000)

    usage = statusbar.read_latest_context_usage(tmp_path)

    assert usage.percent == 73.9
    assert usage.level == "WARNING"


def test_statusbar_usa_last_token_usage_no_total(tmp_path: Path) -> None:
    session = tmp_path / ".codex" / "sessions" / "2026" / "05" / "10" / "rollout-demo.jsonl"
    write_session(session, 1000, total_tokens=90000, context_window=100000)

    usage = statusbar.read_latest_context_usage(tmp_path)

    assert usage.percent == 1.0


def test_statusbar_reporta_nd_sin_sesion(tmp_path: Path) -> None:
    usage = statusbar.read_latest_context_usage(tmp_path)

    assert usage.percent is None
    assert usage.level == "UNKNOWN"


def test_statusbar_categoriza_ok_warning_critical() -> None:
    assert statusbar.ContextUsage(69.9, 1, 1, None).level == "OK"
    assert statusbar.ContextUsage(70.0, 1, 1, None).level == "WARNING"
    assert statusbar.ContextUsage(85.0, 1, 1, None).level == "CRITICAL"


def test_statusbar_muestra_env_stale(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(statusbar, "read_latest_context_usage", lambda home=None: statusbar.ContextUsage(None, None, None, None))
    monkeypatch.setattr(statusbar, "_rtk_gain_summary", lambda timeout=3: None)
    monkeypatch.setattr(
        statusbar,
        "check_environment",
        lambda root: EnvReport("OK", "Env OK", "x", "0.3.0", "0.3.0", "pipx", False, ()),
    )
    monkeypatch.setattr(
        statusbar,
        "check_stale",
        lambda root: StaleReport("STALE", "stale", (), "OK", "Env OK", "fingerprint", None),
    )

    line = statusbar.build_statusbar_line(tmp_path, include_rtk=False, home=tmp_path)

    assert "CTX n/d" in line
    assert "Env STALE" in line
    assert "Alert no" in line


def test_statusbar_muestra_alerta_no_y_si(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(statusbar, "read_latest_context_usage", lambda home=None: statusbar.ContextUsage(None, None, None, None))
    monkeypatch.setattr(statusbar, "_rtk_gain_summary", lambda timeout=3: None)
    monkeypatch.setattr(
        statusbar,
        "check_environment",
        lambda root: EnvReport("OK", "Env OK", "x", "0.3.0", "0.3.0", "pipx", False, ()),
    )
    monkeypatch.setattr(
        statusbar,
        "check_stale",
        lambda root: StaleReport("OK", "ok", (), "OK", "Env OK", "fingerprint", None),
    )

    assert "Alert no" in statusbar.build_statusbar_line(tmp_path, include_rtk=False, home=tmp_path)
    alert = tmp_path / ".llm-toolkit" / "alerts" / "CODEX_ALERT.md"
    alert.parent.mkdir(parents=True)
    alert.write_text("# alerta\n", encoding="utf-8")

    assert "Alert sí" in statusbar.build_statusbar_line(tmp_path, include_rtk=False, home=tmp_path)


def test_statusbar_muestra_rtk_nd_si_no_hay_gain(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(statusbar, "read_latest_context_usage", lambda home=None: statusbar.ContextUsage(None, None, None, None))
    monkeypatch.setattr(statusbar, "_rtk_gain_summary", lambda timeout=3: None)
    monkeypatch.setattr(
        statusbar,
        "check_environment",
        lambda root: EnvReport("OK", "Env OK", "x", "0.3.0", "0.3.0", "pipx", False, ()),
    )
    monkeypatch.setattr(
        statusbar,
        "check_stale",
        lambda root: StaleReport("OK", "ok", (), "OK", "Env OK", "fingerprint", None),
    )

    assert "RTK n/d" in statusbar.build_statusbar_line(tmp_path, include_rtk=True, home=tmp_path)
