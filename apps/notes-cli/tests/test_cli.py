from typer.testing import CliRunner

from notes_cli.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout == "notes-cli 0.1.0\n"
