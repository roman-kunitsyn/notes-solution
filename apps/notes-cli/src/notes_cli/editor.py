from dataclasses import dataclass


@dataclass(frozen=True)
class NoteDraft:
    title: str
    content: str


def render_draft(title: str, content: str) -> str:
    return f"# {title}\n\n{content.rstrip()}\n"


def parse_draft(text: str) -> NoteDraft:
    lines = text.splitlines()

    if not lines or not lines[0].startswith("# "):
        raise ValueError("The first line must contain the title in '# Title' format")

    title = lines[0][2:].strip()

    if not title:
        raise ValueError("Note title cannot be empty")

    content_lines = lines[1:]

    if content_lines and content_lines[0] == "":
        content_lines = content_lines[1:]

    content = "\n".join(content_lines).rstrip()

    return NoteDraft(
        title=title,
        content=content,
    )
