from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from aiohttp import ClientSession
from aiohttp.test_utils import (
    TestClient,
    TestServer,
)

from notes_bot.http_server import (
    HttpServer,
    create_http_app,
)
from notes_bot.linking import create_link_challenge


@asynccontextmanager
async def http_test_client(
    database_path: Path,
) -> AsyncIterator[TestClient]:
    server = TestServer(create_http_app(database_path=database_path))
    client = TestClient(server)

    await client.start_server()

    try:
        yield client
    finally:
        await client.close()


async def test_health_endpoint(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.get("/health")

        assert response.status == 200
        assert await response.json() == {"status": "ok"}
        assert response.headers["Cache-Control"] == "no-store"


async def test_link_page_has_security_headers(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.get("/link")
        text = await response.text()

        assert response.status == 200
        assert "Link Notes account" in text
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'none'" in (response.headers["Content-Security-Policy"])


async def test_validate_link_accepts_valid_challenge(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=100,
    )

    async with http_test_client(path) as client:
        response = await client.post(
            "/link/validate",
            json={"token": challenge.token},
        )

        assert response.status == 200
        assert await response.json() == {"valid": True}


async def test_validate_link_rejects_unknown_token(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.post(
            "/link/validate",
            json={"token": "x" * 43},
        )

        assert response.status == 404


async def test_validate_link_rejects_bad_format(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.post(
            "/link/validate",
            json={"token": "invalid"},
        )

        assert response.status == 400


async def test_validation_does_not_consume_link(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=100,
    )

    async with http_test_client(path) as client:
        first = await client.post(
            "/link/validate",
            json={"token": challenge.token},
        )
        second = await client.post(
            "/link/validate",
            json={"token": challenge.token},
        )

        assert first.status == 200
        assert second.status == 200


async def test_http_server_start_and_stop(
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    server = HttpServer(
        application=create_http_app(database_path=(tmp_path / "bot.sqlite3")),
        host="127.0.0.1",
        port=unused_tcp_port,
    )

    assert server.started is False

    await server.start()

    try:
        assert server.started is True

        async with ClientSession() as client:
            response = await client.get(f"http://127.0.0.1:{unused_tcp_port}/health")

            assert response.status == 200
            assert await response.json() == {"status": "ok"}
    finally:
        await server.stop()

    assert server.started is False


async def test_http_server_stop_before_start(
    tmp_path: Path,
) -> None:
    server = HttpServer(
        application=create_http_app(database_path=(tmp_path / "bot.sqlite3")),
        host="127.0.0.1",
        port=8080,
    )

    await server.stop()

    assert server.started is False
