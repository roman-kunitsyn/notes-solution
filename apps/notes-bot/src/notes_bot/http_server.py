import asyncio
import re
from pathlib import Path
from typing import Protocol

from aiohttp import web

from notes_bot.linking import inspect_link_challenge
from notes_bot.otp_state import (
    ChallengeEmailMismatch,
    InvalidLinkChallenge,
    OtpAttemptsExceeded,
    OtpNotRequested,
    OtpRequestTooSoon,
)
from notes_bot.sessions import (
    LinkCompletionError,
    SessionAlreadyLinked,
)
from notes_bot.supabase_otp import (
    InvalidOtpCode,
    OtpDeliveryError,
    OtpVerificationError,
)

DATABASE_PATH = web.AppKey(
    "database_path",
    Path,
)


class OtpRequester(Protocol):
    async def request_code(
        self,
        *,
        token: str,
        email: str,
    ) -> object: ...

    async def verify_code(
        self,
        *,
        token: str,
        email: str,
        code: str,
    ) -> object: ...


OTP_SERVICE = web.AppKey(
    "otp_service",
    OtpRequester,
)

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")

REQUEST_OTP_SUCCESS = {
    "ok": True,
    "message": "If the account can be authenticated, a code has been sent.",
}
REQUEST_OTP_CLIENT_ERROR = {
    "ok": False,
    "error": "Unable to request an authentication code.",
}
REQUEST_OTP_SERVICE_ERROR = {
    "ok": False,
    "error": "Authentication is temporarily unavailable.",
}
VERIFY_OTP_SUCCESS = {
    "ok": True,
    "message": "Your account has been linked successfully.",
}
VERIFY_OTP_CLIENT_ERROR = {
    "ok": False,
    "error": "Unable to verify the authentication code.",
}
VERIFY_OTP_INVALID_CODE_ERROR = {
    "ok": False,
    "error": "The authentication code is invalid or expired.",
}
VERIFY_OTP_ATTEMPTS_ERROR = {
    "ok": False,
    "error": "Too many unsuccessful verification attempts.",
}
VERIFY_OTP_CONFLICT_ERROR = {
    "ok": False,
    "error": "This account cannot be linked.",
}
VERIFY_OTP_SERVICE_ERROR = {
    "ok": False,
    "error": "Authentication is temporarily unavailable.",
}

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "style-src 'self'; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


LINK_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
  >
  <title>Link Notes account</title>
  <link rel="stylesheet" href="/assets/link.css">
</head>
<body>
  <main>
    <h1>Link Notes account</h1>
    <p
      id="status"
      role="status"
      aria-live="polite"
    >Checking your secure link...</p>

    <form id="email-form" hidden>
      <h2>Verify your email</h2>
      <p>Enter the email address for your existing Notes account.</p>
      <label for="email-input">Email address</label>
      <input
        id="email-input"
        name="email"
        type="email"
        autocomplete="email"
        required
      >
      <button type="submit">Send code</button>
      <p
        id="email-message"
        class="message"
        role="status"
        aria-live="polite"
      ></p>
    </form>

    <form id="otp-form" hidden>
      <h2>Enter authentication code</h2>
      <p>Enter the authentication code from your email.</p>
      <label for="otp-input">Authentication code</label>
      <input
        id="otp-input"
        name="code"
        inputmode="numeric"
        autocomplete="one-time-code"
        maxlength="6"
        pattern="[0-9]{6}"
        required
      >
      <button type="submit">Link account</button>
      <p
        id="otp-message"
        class="message"
        role="status"
        aria-live="polite"
      ></p>
    </form>

    <section id="success-panel" hidden>
      <h2>Account linked</h2>
      <p>Your account has been linked successfully. You can return to Telegram.</p>
    </section>
  </main>
  <script src="/assets/link.js"></script>
</body>
</html>
"""


LINK_SCRIPT = """const emailForm =
  document.getElementById("email-form");
const emailInput =
  document.getElementById("email-input");
const emailMessageElement =
  document.getElementById("email-message");
const otpForm =
  document.getElementById("otp-form");
const otpInput =
  document.getElementById("otp-input");
const otpMessageElement =
  document.getElementById("otp-message");
const statusElement =
  document.getElementById("status");
const successPanel =
  document.getElementById("success-panel");

let challengeToken = new URLSearchParams(
  window.location.hash.slice(1)
).get("token");
let submittedEmail = "";

history.replaceState(
  null,
  "",
  window.location.pathname
);

const temporaryMessage =
  "Authentication is temporarily unavailable. Please try again.";
const terminalLinkMessage =
  "This link can no longer be used. Return to Telegram and create a new link.";
const invalidCodeMessage =
  "The authentication code is invalid or expired.";
const approvedServerMessages = new Set([
  "Unable to verify the authentication code.",
  invalidCodeMessage,
  "Too many unsuccessful verification attempts.",
  "This account cannot be linked.",
  "Authentication is temporarily unavailable."
]);

function hide(element) {
  element.hidden = true;
}

function show(element) {
  element.hidden = false;
}

function setFormDisabled(form, disabled) {
  for (const control of form.querySelectorAll("input, button")) {
    control.disabled = disabled;
  }
}

function setStatus(message) {
  statusElement.textContent = message;
}

function setEmailMessage(message) {
  emailMessageElement.textContent = message;
}

function setOtpMessage(message) {
  otpMessageElement.textContent = message;
}

function showEmailForm() {
  hide(otpForm);
  hide(successPanel);
  show(emailForm);
  setStatus("Enter the email address for your existing Notes account.");
  setEmailMessage("");
  emailInput.focus();
}

function showOtpForm(message) {
  hide(emailForm);
  hide(successPanel);
  show(otpForm);
  setStatus(message);
  setOtpMessage("");
  otpInput.focus();
}

function showTerminalFailure(message) {
  hide(emailForm);
  hide(otpForm);
  hide(successPanel);
  setStatus(message);
}

function showSuccess() {
  hide(emailForm);
  hide(otpForm);
  show(successPanel);
  setStatus("Your account has been linked successfully. You can return to Telegram.");
}

function safeErrorMessage(payload, fallback) {
  if (
    payload &&
    typeof payload.error === "string" &&
    approvedServerMessages.has(payload.error)
  ) {
    return payload.error;
  }

  return fallback;
}

async function postJson(path, data) {
  const response = await fetch(
    path,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(data)
    }
  );

  let payload = {};

  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  return {response, payload};
}

async function validateLink() {
  if (!challengeToken) {
    showTerminalFailure(terminalLinkMessage);
    return;
  }

  try {
    const {response} = await postJson(
      "/link/validate",
      {token: challengeToken}
    );

    if (!response.ok) {
      showTerminalFailure(terminalLinkMessage);
      return;
    }

    showEmailForm();
  } catch {
    setStatus(temporaryMessage);
  }
}

emailForm.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    if (!challengeToken) {
      showTerminalFailure(terminalLinkMessage);
      return;
    }

    const email = emailInput.value.trim();
    emailInput.value = email;

    if (!email || !emailInput.checkValidity()) {
      setEmailMessage("Enter a valid email address.");
      emailInput.focus();
      return;
    }

    setFormDisabled(emailForm, true);
    setStatus("Requesting authentication code...");
    setEmailMessage("");

    try {
      const {response} = await postJson(
        "/link/request-otp",
        {
          token: challengeToken,
          email
        }
      );

      if (response.status === 202) {
        submittedEmail = email;
        showOtpForm(
          "If the account can be authenticated, a code has been sent."
        );
        setFormDisabled(emailForm, false);
        return;
      }

      if (response.status === 429) {
        const retryAfter = response.headers.get("Retry-After");
        const waitMessage = retryAfter
          ? `Please wait ${retryAfter} seconds before requesting another code.`
          : "Please wait before requesting another code.";

        setStatus(waitMessage);
        setFormDisabled(emailForm, false);
        return;
      }

      if (response.status === 503) {
        setStatus(temporaryMessage);
        setFormDisabled(emailForm, false);
        return;
      }

      showTerminalFailure(terminalLinkMessage);
    } catch {
      setStatus(temporaryMessage);
      setFormDisabled(emailForm, false);
    }
  }
);

otpForm.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    if (!challengeToken || !submittedEmail) {
      showTerminalFailure(terminalLinkMessage);
      return;
    }

    const code = otpInput.value.trim();
    otpInput.value = code;

    if (!/^[0-9]{6}$/.test(code)) {
      setOtpMessage(invalidCodeMessage);
      otpInput.focus();
      return;
    }

    setFormDisabled(otpForm, true);
    setStatus("Verifying authentication code...");
    setOtpMessage("");

    try {
      const {response, payload} = await postJson(
        "/link/verify-otp",
        {
          token: challengeToken,
          email: submittedEmail,
          code
        }
      );

      if (response.status === 200) {
        otpInput.value = "";
        emailInput.value = "";
        challengeToken = "";
        submittedEmail = "";
        showSuccess();
        setFormDisabled(otpForm, false);
        return;
      }

      if (response.status === 400) {
        const message = safeErrorMessage(
          payload,
          "Unable to verify the authentication code."
        );

        if (message === invalidCodeMessage) {
          otpInput.value = "";
          setOtpMessage(message);
          setFormDisabled(otpForm, false);
          otpInput.focus();
          return;
        }

        showTerminalFailure(terminalLinkMessage);
        return;
      }

      if (response.status === 409) {
        showTerminalFailure("This account cannot be linked.");
        return;
      }

      if (response.status === 429) {
        showTerminalFailure("Too many unsuccessful verification attempts.");
        return;
      }

      if (response.status === 503) {
        setStatus(
          safeErrorMessage(payload, "Authentication is temporarily unavailable.")
        );
        setFormDisabled(otpForm, false);
        return;
      }

      showTerminalFailure(terminalLinkMessage);
    } catch {
      setStatus(temporaryMessage);
      setFormDisabled(otpForm, false);
    }
  }
);

void validateLink();
"""


LINK_STYLE = """body {
  box-sizing: border-box;
  margin: 0;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  font-family: system-ui, sans-serif;
  background: #f6f7f9;
  color: #17191c;
}

main {
  width: min(100%, 32rem);
  padding: 2rem;
  border-radius: 0.75rem;
  background: white;
  box-shadow: 0 0.5rem 2rem rgb(0 0 0 / 8%);
}

h1 {
  margin-top: 0;
}

h2 {
  margin: 1.5rem 0 0.5rem;
  font-size: 1.125rem;
}

form,
section {
  display: grid;
  gap: 0.75rem;
}

[hidden] {
  display: none;
}

label {
  font-weight: 600;
}

input {
  box-sizing: border-box;
  width: 100%;
  min-height: 2.75rem;
  padding: 0.625rem 0.75rem;
  border: 1px solid #b9c0cc;
  border-radius: 0.5rem;
  font: inherit;
}

button {
  min-height: 2.75rem;
  padding: 0.625rem 1rem;
  border: 0;
  border-radius: 0.5rem;
  font: inherit;
  font-weight: 700;
  color: white;
  background: #1f6feb;
  cursor: pointer;
}

button:disabled,
input:disabled {
  cursor: wait;
  opacity: 0.65;
}

.message {
  min-height: 1.5rem;
  margin: 0;
}
"""


def secure_response(
    *,
    text: str,
    content_type: str,
    status: int = 200,
) -> web.Response:
    return web.Response(
        text=text,
        content_type=content_type,
        status=status,
        headers=SECURITY_HEADERS,
    )


def secure_json_response(
    data: dict[str, object],
    *,
    status: int,
    headers: dict[str, str] | None = None,
) -> web.Response:
    response_headers = dict(SECURITY_HEADERS)

    if headers is not None:
        response_headers.update(headers)

    return web.json_response(
        data,
        status=status,
        headers=response_headers,
    )


async def health_handler(
    request: web.Request,
) -> web.Response:
    return web.json_response(
        {"status": "ok"},
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def parse_request_otp_payload(payload: object) -> tuple[str, str] | None:
    if not isinstance(payload, dict):
        return None

    token = payload.get("token")
    email = payload.get("email")

    if (
        not isinstance(token, str)
        or not token.strip()
        or TOKEN_PATTERN.fullmatch(token) is None
    ):
        return None

    if not isinstance(email, str) or not email.strip():
        return None

    return token, email


def parse_verify_otp_payload(payload: object) -> tuple[str, str, str] | None:
    if not isinstance(payload, dict):
        return None

    token = payload.get("token")
    email = payload.get("email")
    code = payload.get("code")

    if (
        not isinstance(token, str)
        or not token.strip()
        or TOKEN_PATTERN.fullmatch(token) is None
    ):
        return None

    if not isinstance(email, str) or not email.strip():
        return None

    if not isinstance(code, str) or not code.strip():
        return None

    return token, email, code


async def link_page_handler(
    request: web.Request,
) -> web.Response:
    return secure_response(
        text=LINK_PAGE,
        content_type="text/html",
    )


async def link_script_handler(
    request: web.Request,
) -> web.Response:
    return secure_response(
        text=LINK_SCRIPT,
        content_type="application/javascript",
    )


async def link_style_handler(
    request: web.Request,
) -> web.Response:
    return secure_response(
        text=LINK_STYLE,
        content_type="text/css",
    )


async def request_otp_handler(
    request: web.Request,
) -> web.Response:
    try:
        payload = await request.json()
    except ValueError, TypeError, web.HTTPException:
        return secure_json_response(
            REQUEST_OTP_CLIENT_ERROR,
            status=400,
        )

    parsed = parse_request_otp_payload(payload)

    if parsed is None:
        return secure_json_response(
            REQUEST_OTP_CLIENT_ERROR,
            status=400,
        )

    token, email = parsed

    try:
        service = request.app[OTP_SERVICE]
    except KeyError:
        return secure_json_response(
            REQUEST_OTP_SERVICE_ERROR,
            status=503,
        )

    try:
        await service.request_code(
            token=token,
            email=email,
        )
    except OtpRequestTooSoon as error:
        return secure_json_response(
            REQUEST_OTP_CLIENT_ERROR,
            status=429,
            headers={"Retry-After": str(error.retry_after)},
        )
    except (
        ChallengeEmailMismatch,
        InvalidLinkChallenge,
        OtpAttemptsExceeded,
        OtpNotRequested,
        ValueError,
    ):
        return secure_json_response(
            REQUEST_OTP_CLIENT_ERROR,
            status=400,
        )
    except OtpDeliveryError:
        return secure_json_response(
            REQUEST_OTP_SERVICE_ERROR,
            status=503,
        )

    return secure_json_response(
        REQUEST_OTP_SUCCESS,
        status=202,
    )


async def verify_otp_handler(
    request: web.Request,
) -> web.Response:
    try:
        payload = await request.json()
    except ValueError, TypeError, web.HTTPException:
        return secure_json_response(
            VERIFY_OTP_CLIENT_ERROR,
            status=400,
        )

    parsed = parse_verify_otp_payload(payload)

    if parsed is None:
        return secure_json_response(
            VERIFY_OTP_CLIENT_ERROR,
            status=400,
        )

    token, email, code = parsed

    try:
        service = request.app[OTP_SERVICE]
    except KeyError:
        return secure_json_response(
            VERIFY_OTP_SERVICE_ERROR,
            status=503,
        )

    try:
        await service.verify_code(
            token=token,
            email=email,
            code=code,
        )
    except InvalidOtpCode:
        return secure_json_response(
            VERIFY_OTP_INVALID_CODE_ERROR,
            status=400,
        )
    except OtpAttemptsExceeded:
        return secure_json_response(
            VERIFY_OTP_ATTEMPTS_ERROR,
            status=429,
        )
    except (
        ChallengeEmailMismatch,
        InvalidLinkChallenge,
        LinkCompletionError,
        OtpNotRequested,
        ValueError,
    ):
        return secure_json_response(
            VERIFY_OTP_CLIENT_ERROR,
            status=400,
        )
    except SessionAlreadyLinked:
        return secure_json_response(
            VERIFY_OTP_CONFLICT_ERROR,
            status=409,
        )
    except OtpVerificationError:
        return secure_json_response(
            VERIFY_OTP_SERVICE_ERROR,
            status=503,
        )

    return secure_json_response(
        VERIFY_OTP_SUCCESS,
        status=200,
    )


async def validate_link_handler(
    request: web.Request,
) -> web.Response:
    try:
        payload = await request.json()
    except ValueError, TypeError:
        raise web.HTTPBadRequest(
            text="Invalid request",
            headers=SECURITY_HEADERS,
        )

    token = payload.get("token")

    if not isinstance(token, str) or TOKEN_PATTERN.fullmatch(token) is None:
        raise web.HTTPBadRequest(
            text="Invalid request",
            headers=SECURITY_HEADERS,
        )

    identity = await asyncio.to_thread(
        inspect_link_challenge,
        request.app[DATABASE_PATH],
        token,
    )

    if identity is None:
        raise web.HTTPNotFound(
            text="Link is invalid or expired",
            headers=SECURITY_HEADERS,
        )

    # Do not expose Telegram identifiers to the browser.
    return web.json_response(
        {"valid": True},
        headers=SECURITY_HEADERS,
    )


def create_http_app(
    *,
    database_path: Path,
    otp_service: OtpRequester | None = None,
) -> web.Application:
    application = web.Application(
        client_max_size=4 * 1024,
    )
    application[DATABASE_PATH] = database_path

    if otp_service is not None:
        application[OTP_SERVICE] = otp_service

    application.router.add_get(
        "/health",
        health_handler,
    )
    application.router.add_get(
        "/link",
        link_page_handler,
    )
    application.router.add_get(
        "/assets/link.js",
        link_script_handler,
    )
    application.router.add_get(
        "/assets/link.css",
        link_style_handler,
    )
    application.router.add_post(
        "/link/validate",
        validate_link_handler,
    )
    application.router.add_post(
        "/link/request-otp",
        request_otp_handler,
    )
    application.router.add_post(
        "/link/verify-otp",
        verify_otp_handler,
    )

    return application


class HttpServer:
    def __init__(
        self,
        *,
        application: web.Application,
        host: str,
        port: int,
    ) -> None:
        self._application = application
        self._host = host
        self._port = port
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    @property
    def started(self) -> bool:
        return self._runner is not None

    async def start(self) -> None:
        if self.started:
            raise RuntimeError("HTTP server is already running")

        runner = web.AppRunner(self._application)

        try:
            await runner.setup()

            site = web.TCPSite(
                runner,
                host=self._host,
                port=self._port,
            )

            await site.start()
        except Exception:
            await runner.cleanup()
            raise

        self._runner = runner
        self._site = site

    async def stop(self) -> None:
        runner = self._runner

        if runner is None:
            return

        self._runner = None
        self._site = None

        await runner.cleanup()
