from httpx import HTTPError
from postgrest.exceptions import APIError
from storage3.exceptions import StorageApiError
from supabase_auth.errors import AuthApiError

from notes_cli.client import AuthenticationRequired
from notes_cli.config import ConfigurationError


def error_code(error: Exception) -> str:
    return str(getattr(error, "code", "") or "")


def error_status(error: Exception) -> int | None:
    value = getattr(error, "status", None)

    if value is None:
        value = getattr(error, "status_code", None)

    try:
        return int(value) if value is not None else None
    except TypeError, ValueError:
        return None


def error_message(error: Exception) -> str:
    if isinstance(
        error,
        (ConfigurationError, AuthenticationRequired, ValueError),
    ):
        return str(error)

    if isinstance(error, AuthApiError):
        code = error_code(error)
        message = str(error).lower()

        if code in {"invalid_credentials", "invalid_grant"} or (
            "invalid login credentials" in message
        ):
            return "Invalid email or password"

        if code == "email_not_confirmed":
            return "Email address has not been confirmed"

        if code in {
            "refresh_token_not_found",
            "refresh_token_already_used",
            "session_not_found",
        }:
            return "Session expired. Run: notes login"

        if code in {
            "user_already_exists",
            "email_exists",
        }:
            return "A user with this email already exists"

        if code == "weak_password":
            return "Password does not satisfy the security requirements"

        return f"Authentication failed: {error}"

    if isinstance(error, APIError):
        code = error_code(error)
        message = str(getattr(error, "message", error))

        if code == "42501":
            return "Operation denied by the database access policy"

        if code == "23505":
            return "A conflicting database record already exists"

        if code.startswith("PGRST"):
            return f"Database API request failed: {message}"

        return f"Database request failed: {message}"

    if isinstance(error, StorageApiError):
        status = error_status(error)
        message = str(error)
        lowered = message.lower()

        if status == 409 or "already exists" in lowered:
            return "Attachment already exists. Use --replace to overwrite it"

        if status == 413 or "too large" in lowered:
            return "Attachment exceeds the Storage size limit"

        if "mime type" in lowered:
            return "Storage rejected the attachment type"

        if status in {401, 403}:
            return "Storage access denied"

        if status == 404 or "not found" in lowered:
            return "Attachment not found"

        return f"Storage request failed: {message}"

    if isinstance(error, HTTPError):
        return "Cannot connect to Supabase. Check the URL and server status"

    message = str(error).strip()

    if message:
        return message

    return error.__class__.__name__
