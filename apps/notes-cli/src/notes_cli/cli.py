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


if __name__ == "__main__":
    app()
