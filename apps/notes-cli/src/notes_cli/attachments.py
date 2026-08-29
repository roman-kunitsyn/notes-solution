import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from notes_cli.client import authenticated_client

BUCKET = "note-attachments"
MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
}


@dataclass(frozen=True)
class Attachment:
    name: str
    size: int
    created_at: str


def validate_filename(filename: str) -> str:
    if not filename or filename in {".", ".."}:
        raise ValueError("Invalid attachment filename")

    if "/" in filename or "\\" in filename:
        raise ValueError("Attachment filename cannot contain directories")

    return filename


def attachment_path(
    user_id: str,
    note_id: str,
    filename: str,
) -> str:
    validated = validate_filename(filename)
    return f"{user_id}/{note_id}/{validated}"


def authenticated_storage():
    client = authenticated_client()
    response = client.auth.get_user()

    if response.user is None:
        raise RuntimeError("Authenticated session has no user")

    return client, response.user.id


def upload_attachment(
    note_id: str,
    local_path: Path,
    *,
    replace: bool = False,
) -> str:
    source = local_path.expanduser().resolve()

    if not source.is_file():
        raise ValueError(f"File not found: {source}")

    size = source.stat().st_size

    if size > MAX_FILE_SIZE:
        raise ValueError("Attachment exceeds the 10 MiB limit")

    mime_type, _ = mimetypes.guess_type(source.name)

    if mime_type not in ALLOWED_MIME_TYPES:
        allowed = ", ".join(sorted(ALLOWED_MIME_TYPES))
        raise ValueError(
            f"Unsupported file type: {mime_type or 'unknown'}. Allowed types: {allowed}"
        )

    client, user_id = authenticated_storage()
    remote_path = attachment_path(user_id, note_id, source.name)

    with source.open("rb") as file:
        client.storage.from_(BUCKET).upload(
            path=remote_path,
            file=file,
            file_options={
                "content-type": mime_type,
                "upsert": "true" if replace else "false",
            },
        )

    return remote_path


def list_attachments(note_id: str) -> list[Attachment]:
    client, user_id = authenticated_storage()
    folder = f"{user_id}/{note_id}"

    rows: list[dict[str, Any]] = client.storage.from_(BUCKET).list(
        folder,
        {
            "limit": 100,
            "offset": 0,
            "sortBy": {
                "column": "name",
                "order": "asc",
            },
        },
    )

    attachments = []

    for row in rows:
        metadata = row.get("metadata") or {}

        attachments.append(
            Attachment(
                name=str(row["name"]),
                size=int(metadata.get("size") or 0),
                created_at=str(row.get("created_at") or ""),
            )
        )

    return attachments


def download_attachment(
    note_id: str,
    filename: str,
) -> bytes:
    client, user_id = authenticated_storage()
    remote_path = attachment_path(user_id, note_id, filename)

    return client.storage.from_(BUCKET).download(remote_path)


def delete_attachment(
    note_id: str,
    filename: str,
) -> None:
    client, user_id = authenticated_storage()
    remote_path = attachment_path(user_id, note_id, filename)

    client.storage.from_(BUCKET).remove([remote_path])
