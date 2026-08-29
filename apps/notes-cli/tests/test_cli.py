from typer.testing import CliRunner

from notes_cli.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout == "notes-cli 0.1.0\n"


def test_edit_requires_a_change() -> None:
    result = runner.invoke(app, ["edit", "note-id"])

    assert result.exit_code == 2
    assert "provide --title, --content, or both" in result.output


def test_create_rejects_empty_title() -> None:
    result = runner.invoke(
        app,
        [
            "create",
            "--title",
            "   ",
        ],
    )

    assert result.exit_code == 2
    assert "title cannot be empty" in result.output
