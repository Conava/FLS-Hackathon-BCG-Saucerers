"""ASGI middleware that assigns a request-id to every incoming request.

Behaviour:
- If the incoming request carries an ``X-Request-ID`` header, that value is
  reused (useful for tracing across service boundaries).
- Otherwise a new UUID4 is generated.
- The request-id is stored in :data:`~app.core.logging.request_id_var` so
  that all log statements emitted during the request automatically include it.
- The request-id is echoed back in the ``X-Request-ID`` response header.

PHI note: request-ids are random UUIDs — they contain no patient data.
"""
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that generates/propagates ``X-Request-ID``.

    Mount on a FastAPI or Starlette application::

        app.add_middleware(RequestIdMiddleware)

    The middleware guarantees that:
    1. Every request has a ``request_id`` in context for the duration of the call.
    2. The same ``request_id`` appears in the response ``X-Request-ID`` header.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request, inject request_id, call downstream, echo header."""
        incoming = request.headers.get(_HEADER)
        request_id = incoming if incoming else str(uuid.uuid4())

        # Store in contextvar so log records pick it up automatically.
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            # Always reset the contextvar — even if the handler raises.
            request_id_var.reset(token)

        response.headers[_HEADER] = request_id
        return response
