import pytest

from notes_cli.editor import NoteDraft, parse_draft, render_draft


def test_draft_round_trip() -> None:
    rendered = render_draft(
        "Example title",
        "First line\nSecond line",
    )

    assert parse_draft(rendered) == NoteDraft(
        title="Example title",
        content="First line\nSecond line",
    )


def test_parse_draft_requires_markdown_title() -> None:
    with pytest.raises(ValueError):
        parse_draft("Missing heading\n\nContent")


def test_parse_draft_rejects_empty_title() -> None:
    with pytest.raises(ValueError):
        parse_draft("#   \n\nContent")
