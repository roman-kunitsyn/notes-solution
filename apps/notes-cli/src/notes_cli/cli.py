import os
from pathlib import Path
from typing import Annotated

import typer

from notes_cli.attachments import (
    delete_attachment,
    download_attachment,
    list_attachments,
    upload_attachment,
)
from notes_cli.client import (
    AuthenticationRequired,
    current_user,
)
from notes_cli.client import (
    login as login_user,
)
from notes_cli.client import (
    logout as logout_user,
)
from notes_cli.config import (
    ConfigurationError,
    Settings,
    load_settings,
    remove_settings,
    save_settings,
    settings_path,
)
from notes_cli.notes import (
    Note,
    create_note,
    delete_note,
    get_note,
    list_notes,
    update_note,
)
from notes_cli.session import remove_session

app = typer.Typer(
    name="notes",
    help="Personal notes client for self-hosted Supabase.",
    no_args_is_help=True,
)

config_app = typer.Typer(
    help="Manage the Supabase connection configuration.",
    no_args_is_help=True,
)

app.add_typer(config_app, name="config")


def show_error(error: Exception) -> None:
    typer.echo(f"Error: {error}", err=True)


@app.callback()
def main() -> None:
    """Personal notes client for self-hosted Supabase."""


@app.command()
def version() -> None:
    """Show the Notes CLI version."""
    typer.echo("notes-cli 0.1.0")


@app.command()
def login(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(
        ...,
        prompt=True,
        hide_input=True,
    ),
) -> None:
    """Sign in using email and password."""
    try:
        identity = login_user(email, password)
    except (ConfigurationError, RuntimeError, Exception) as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    typer.echo(f"Logged in as {identity}")


@app.command()
def logout() -> None:
    """Sign out and remove the local session."""
    try:
        logout_user()
    except (ConfigurationError, RuntimeError, Exception) as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    typer.echo("Logged out")


@app.command()
def whoami() -> None:
    """Show the authenticated user."""
    try:
        user_id, email = current_user()
    except (ConfigurationError, AuthenticationRequired, Exception) as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    typer.echo(f"User ID: {user_id}")
    typer.echo(f"Email: {email}")


def show_note(note: Note, include_content: bool = True) -> None:
    typer.echo(f"ID: {note.id}")
    typer.echo(f"Title: {note.title}")
    typer.echo(f"Updated: {note.updated_at}")

    if include_content:
        typer.echo()
        typer.echo(note.content or "")


@app.command("list")
def list_notes_command(
    limit: int = typer.Option(
        50,
        min=1,
        max=1000,
        help="Maximum number of notes to return.",
    ),
) -> None:
    """List the authenticated user's notes."""
    try:
        notes = list_notes(limit)
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    if not notes:
        typer.echo("No notes")
        return

    for note in notes:
        typer.echo(f"{note.id}  {note.updated_at}  {note.title}")


@app.command()
def show(note_id: str) -> None:
    """Show one note by ID."""
    try:
        note = get_note(note_id)
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    if note is None:
        typer.echo("Note not found", err=True)
        raise typer.Exit(code=1)

    show_note(note)


@app.command()
def create(
    title: str = typer.Option(
        ...,
        prompt=True,
        help="Note title.",
    ),
    content: str = typer.Option(
        "",
        help="Note content.",
    ),
) -> None:
    """Create a note."""
    title = title.strip()

    if not title:
        typer.echo("Error: title cannot be empty", err=True)
        raise typer.Exit(code=2)

    try:
        note = create_note(title, content)
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    typer.echo("Note created")
    show_note(note)


@app.command()
def edit(
    note_id: str,
    title: str | None = typer.Option(
        None,
        help="Replace the note title.",
    ),
    content: str | None = typer.Option(
        None,
        help="Replace the note content.",
    ),
) -> None:
    """Edit a note owned by the authenticated user."""
    if title is None and content is None:
        typer.echo(
            "Error: provide --title, --content, or both",
            err=True,
        )
        raise typer.Exit(code=2)

    if title is not None:
        title = title.strip()

        if not title:
            typer.echo("Error: title cannot be empty", err=True)
            raise typer.Exit(code=2)

    try:
        note = update_note(
            note_id,
            title=title,
            content=content,
        )
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    if note is None:
        typer.echo("Note not found", err=True)
        raise typer.Exit(code=1)

    typer.echo("Note updated")
    show_note(note)


@app.command()
def delete(
    note_id: str,
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Delete without asking for confirmation.",
    ),
) -> None:
    """Delete a note owned by the authenticated user."""
    try:
        note = get_note(note_id)
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    if note is None:
        typer.echo("Note not found", err=True)
        raise typer.Exit(code=1)

    if not yes:
        confirmed = typer.confirm(
            f'Delete "{note.title}"?',
            default=False,
        )

        if not confirmed:
            typer.echo("Cancelled")
            return

    try:
        deleted = delete_note(note_id)
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    if deleted is None:
        typer.echo("Note not found", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Deleted: {deleted.title}")


if __name__ == "__main__":
    app()


@app.command()
def attach(
    note_id: str,
    file: Path,
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Replace an existing attachment with the same name.",
    ),
) -> None:
    """Upload a private attachment to a note."""
    try:
        note = get_note(note_id)

        if note is None:
            typer.echo("Note not found", err=True)
            raise typer.Exit(code=1)

        remote_path = upload_attachment(
            note_id,
            file,
            replace=replace,
        )
    except typer.Exit:
        raise
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    typer.echo(f"Uploaded: {remote_path}")


@app.command()
def attachments(note_id: str) -> None:
    """List a note's private attachments."""
    try:
        note = get_note(note_id)

        if note is None:
            typer.echo("Note not found", err=True)
            raise typer.Exit(code=1)

        files = list_attachments(note_id)
    except typer.Exit:
        raise
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    if not files:
        typer.echo("No attachments")
        return

    for attachment in files:
        typer.echo(f"{attachment.size:>10}  {attachment.created_at}  {attachment.name}")


@app.command()
def download(
    note_id: str,
    filename: str,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Destination path. Defaults to the attachment filename.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Overwrite an existing local file.",
        ),
    ] = False,
) -> None:
    """Download a private attachment."""
    destination = output.expanduser() if output is not None else Path(filename)

    if destination.exists() and not force:
        typer.echo(
            f"Error: destination already exists: {destination}",
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        note = get_note(note_id)

        if note is None:
            typer.echo("Note not found", err=True)
            raise typer.Exit(code=1)

        data = download_attachment(note_id, filename)
    except typer.Exit:
        raise
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)

    typer.echo(f"Downloaded: {destination}")


@app.command()
def detach(
    note_id: str,
    filename: str,
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Delete without confirmation.",
    ),
) -> None:
    """Delete a private attachment."""
    if not yes:
        confirmed = typer.confirm(
            f'Delete attachment "{filename}"?',
            default=False,
        )

        if not confirmed:
            typer.echo("Cancelled")
            return

    try:
        note = get_note(note_id)

        if note is None:
            typer.echo("Note not found", err=True)
            raise typer.Exit(code=1)

        delete_attachment(note_id, filename)
    except typer.Exit:
        raise
    except Exception as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    typer.echo(f"Deleted attachment: {filename}")


def mask_key(key: str) -> str:
    if len(key) <= 16:
        return "********"

    return f"{key[:15]}...{key[-4:]}"


@config_app.command("set")
def set_config_command(
    url: Annotated[
        str,
        typer.Option(
            "--url",
            prompt="Supabase URL",
            help="Public Supabase URL.",
        ),
    ],
    key: Annotated[
        str | None,
        typer.Option(
            "--key",
            help="Supabase publishable key.",
        ),
    ] = None,
) -> None:
    """Save the Supabase connection."""
    if key is None:
        key = typer.prompt(
            "Publishable key",
            hide_input=True,
        )

    try:
        settings = Settings(
            supabase_url=url,
            publishable_key=key,
        )
        save_settings(settings)
    except ConfigurationError as error:
        show_error(error)
        raise typer.Exit(code=2) from error

    # A session belongs to one Supabase deployment. Changing the endpoint
    # invalidates the association between the saved session and configuration.
    remove_session()

    typer.echo(f"Configuration saved: {settings_path()}")
    typer.echo("Existing local session removed; run: notes login")


@config_app.command("show")
def show_config_command() -> None:
    """Show the effective configuration without revealing the key."""
    try:
        settings = load_settings()
    except ConfigurationError as error:
        show_error(error)
        raise typer.Exit(code=1) from error

    typer.echo(f"URL: {settings.supabase_url}")
    typer.echo(f"Publishable key: {mask_key(settings.publishable_key)}")
    typer.echo(f"File: {settings_path()}")

    if os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_PUBLISHABLE_KEY"):
        typer.echo("Environment overrides are active")


@config_app.command("path")
def show_config_path() -> None:
    """Show the configuration file location."""
    typer.echo(settings_path())


@config_app.command("clear")
def clear_config_command(
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Clear without confirmation.",
        ),
    ] = False,
) -> None:
    """Remove saved configuration and session."""
    if not yes and not typer.confirm(
        "Remove saved configuration and session?",
        default=False,
    ):
        typer.echo("Cancelled")
        return

    remove_settings()
    remove_session()

    typer.echo("Configuration and session removed")
