from typer.testing import CliRunner

from llm_toolkit import __version__
from llm_toolkit.cli import app


runner = CliRunner()


def test_version_global_no_requiere_subcomando() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"llm-toolkit {__version__}" in result.output


def test_help_global_sigue_funcionando() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "doctor" in result.output
