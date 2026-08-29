import typer

app = typer.Typer(
    name="notes",
    help="Personal notes client for self-hosted Supabase.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Personal notes client for self-hosted Supabase."""


@app.command()
def version() -> None:
    """Show the Notes CLI version."""
    typer.echo("notes-cli 0.1.0")


if __name__ == "__main__":
    app()
