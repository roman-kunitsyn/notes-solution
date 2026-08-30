from pathlib import Path
from urllib.parse import (
    parse_qs,
    urlsplit,
)

from notes_bot.link_service import LinkingService
from notes_bot.linking import (
    inspect_link_challenge,
)


async def test_issue_url_uses_fragment_token(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    service = LinkingService(
        database_path=path,
        base_url="http://127.0.0.1:8080/",
    )

    url = await service.issue_url(
        telegram_user_id=100,
        telegram_chat_id=100,
    )

    parsed = urlsplit(url)
    fragment = parse_qs(parsed.fragment)
    token = fragment["token"][0]

    assert parsed.scheme == "http"
    assert parsed.netloc == "127.0.0.1:8080"
    assert parsed.path == "/link"
    assert parsed.query == ""

    assert (
        inspect_link_challenge(
            path,
            token,
        )
        is not None
    )


async def test_new_url_invalidates_previous_url(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    service = LinkingService(
        database_path=path,
        base_url="http://127.0.0.1:8080",
    )

    previous_url = await service.issue_url(
        telegram_user_id=100,
        telegram_chat_id=100,
    )
    current_url = await service.issue_url(
        telegram_user_id=100,
        telegram_chat_id=100,
    )

    previous_token = parse_qs(urlsplit(previous_url).fragment)["token"][0]
    current_token = parse_qs(urlsplit(current_url).fragment)["token"][0]

    assert (
        inspect_link_challenge(
            path,
            previous_token,
        )
        is None
    )
    assert (
        inspect_link_challenge(
            path,
            current_token,
        )
        is not None
    )
