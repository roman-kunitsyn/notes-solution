import pytest

from notes_cli.attachments import attachment_path, validate_filename


def test_attachment_path() -> None:
    assert (
        attachment_path("user-id", "note-id", "example.txt")
        == "user-id/note-id/example.txt"
    )


@pytest.mark.parametrize(
    "filename",
    [
        "",
        ".",
        "..",
        "../secret.txt",
        "folder/file.txt",
        r"folder\file.txt",
    ],
)
def test_rejects_unsafe_filename(filename: str) -> None:
    with pytest.raises(ValueError):
        validate_filename(filename)
