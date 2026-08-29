from httpx import ConnectError, Request

from notes_cli.client import AuthenticationRequired
from notes_cli.config import ConfigurationError
from notes_cli.errors import error_message


def test_configuration_error_is_preserved() -> None:
    error = ConfigurationError("Missing configuration")

    assert error_message(error) == "Missing configuration"


def test_authentication_required_is_preserved() -> None:
    error = AuthenticationRequired("Run: notes login")

    assert error_message(error) == "Run: notes login"


def test_value_error_is_preserved() -> None:
    assert error_message(ValueError("Invalid filename")) == ("Invalid filename")


def test_http_error_has_friendly_message() -> None:
    request = Request(
        "GET",
        "http://127.0.0.1:8000",
    )
    error = ConnectError(
        "Connection refused",
        request=request,
    )

    assert error_message(error) == (
        "Cannot connect to Supabase. Check the URL and server status"
    )
