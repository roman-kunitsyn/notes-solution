from supabase import Client, create_client
from supabase_auth.errors import AuthApiError

from notes_cli.config import Settings, load_settings
from notes_cli.session import (
    SessionTokens,
    load_session,
    remove_session,
    save_session,
)


class AuthenticationRequired(RuntimeError):
    pass


def create_notes_client(settings: Settings | None = None) -> Client:
    resolved = settings or load_settings()

    return create_client(
        resolved.supabase_url,
        resolved.publishable_key,
    )


def login(email: str, password: str) -> str:
    client = create_notes_client()

    response = client.auth.sign_in_with_password(
        {
            "email": email,
            "password": password,
        }
    )

    if response.session is None or response.user is None:
        raise RuntimeError("Supabase did not return an authenticated session")

    save_session(
        SessionTokens(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
        )
    )

    return response.user.email or response.user.id


def authenticated_client() -> Client:
    tokens = load_session()

    if tokens is None:
        raise AuthenticationRequired("Not logged in. Run: notes login")

    client = create_notes_client()

    try:
        response = client.auth.set_session(
            tokens.access_token,
            tokens.refresh_token,
        )
    except AuthApiError as error:
        remove_session()
        raise AuthenticationRequired("Session expired. Run: notes login") from error

    if response.session is None:
        remove_session()
        raise AuthenticationRequired("Session is invalid. Run: notes login")

    # set_session may refresh an expired access token.
    save_session(
        SessionTokens(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
        )
    )

    return client


def current_user() -> tuple[str, str]:
    client = authenticated_client()
    response = client.auth.get_user()

    if response.user is None:
        raise AuthenticationRequired("Session has no user. Run: notes login")

    return response.user.id, response.user.email or ""


def logout() -> None:
    tokens = load_session()

    if tokens is None:
        return

    client = create_notes_client()

    try:
        client.auth.set_session(
            tokens.access_token,
            tokens.refresh_token,
        )
        client.auth.sign_out()
    finally:
        remove_session()
