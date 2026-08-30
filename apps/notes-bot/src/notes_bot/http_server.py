import asyncio
import re
from pathlib import Path

from aiohttp import web

from notes_bot.linking import inspect_link_challenge

DATABASE_PATH = web.AppKey(
    "database_path",
    Path,
)

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")

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
    <p id="status">Checking your secure link…</p>
  </main>
  <script src="/assets/link.js"></script>
</body>
</html>
"""


LINK_SCRIPT = """const statusElement =
  document.getElementById("status");

const parameters = new URLSearchParams(
  window.location.hash.slice(1)
);
const token = parameters.get("token");

history.replaceState(
  null,
  "",
  window.location.pathname
);

async function validateLink() {
  if (!token) {
    statusElement.textContent =
      "This linking URL is incomplete.";
    return;
  }

  try {
    const response = await fetch(
      "/link/validate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({token})
      }
    );

    if (!response.ok) {
      statusElement.textContent =
        "This linking URL is invalid or expired.";
      return;
    }

    statusElement.textContent =
      "The link is valid. Supabase authentication " +
      "will be added in the next step.";
  } catch {
    statusElement.textContent =
      "Could not contact the linking service.";
  }
}

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
) -> web.Application:
    application = web.Application(
        client_max_size=4 * 1024,
    )
    application[DATABASE_PATH] = database_path

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
