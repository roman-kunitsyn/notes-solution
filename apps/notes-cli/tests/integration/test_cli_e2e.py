import os
import re
from pathlib import Path
from uuid import uuid4

import pytest
from storage3.exceptions import StorageApiError
from supabase import create_client
from typer.testing import CliRunner

from notes_cli.cli import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_SUPABASE_INTEGRATION") != "1",
        reason="Supabase integration tests are disabled",
    ),
]

runner = CliRunner()


def assert_success(result) -> None:
    assert result.exit_code == 0, (
        f"Output:\n{result.output}\nException: {result.exception!r}"
    )


def test_two_user_note_and_storage_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = os.environ["SUPABASE_URL"]
    publishable_key = os.environ["SUPABASE_PUBLISHABLE_KEY"]

    monkeypatch.setenv(
        "NOTES_CLI_CONFIG_DIR",
        str(tmp_path / "config"),
    )

    suffix = uuid4().hex
    roman_email = f"roman-{suffix}@example.test"
    alice_email = f"alice-{suffix}@example.test"
    password = f"Test-{suffix}-Password!"

    bootstrap = create_client(url, publishable_key)

    roman_signup = bootstrap.auth.sign_up(
        {
            "email": roman_email,
            "password": password,
        }
    )
    assert roman_signup.user is not None

    alice_client = create_client(url, publishable_key)
    alice_signup = alice_client.auth.sign_up(
        {
            "email": alice_email,
            "password": password,
        }
    )
    assert alice_signup.user is not None

    roman_id = roman_signup.user.id

    result = runner.invoke(
        app,
        [
            "login",
            "--email",
            roman_email,
            "--password",
            password,
        ],
    )
    assert_success(result)

    result = runner.invoke(
        app,
        [
            "create",
            "--title",
            "Roman integration note",
            "--content",
            "Roman-only content",
        ],
    )
    assert_success(result)

    match = re.search(
        r"ID: ([0-9a-f-]{36})",
        result.output,
    )
    assert match is not None
    roman_note_id = match.group(1)

    source = tmp_path / "roman-private.txt"
    source.write_text(
        "Roman private attachment\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "attach",
            roman_note_id,
            str(source),
        ],
    )
    assert_success(result)

    result = runner.invoke(app, ["logout"])
    assert_success(result)

    result = runner.invoke(
        app,
        [
            "login",
            "--email",
            alice_email,
            "--password",
            password,
        ],
    )
    assert_success(result)

    result = runner.invoke(app, ["list"])
    assert_success(result)
    assert "Roman integration note" not in result.output

    result = runner.invoke(
        app,
        ["show", roman_note_id],
    )
    assert result.exit_code == 1
    assert "Note not found" in result.output

    alice_client.auth.sign_in_with_password(
        {
            "email": alice_email,
            "password": password,
        }
    )

    roman_attachment_path = f"{roman_id}/{roman_note_id}/roman-private.txt"

    with pytest.raises(StorageApiError):
        alice_client.storage.from_("note-attachments").download(roman_attachment_path)
