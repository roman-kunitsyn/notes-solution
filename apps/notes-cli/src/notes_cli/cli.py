import typer

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
from notes_cli.config import ConfigurationError
from notes_cli.notes import (
    Note,
    create_note,
    delete_note,
    get_note,
    list_notes,
    update_note,
)

app = typer.Typer(
    name="notes",
    help="Personal notes client for self-hosted Supabase.",
    no_args_is_help=True,
)


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
