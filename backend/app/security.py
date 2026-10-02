import secrets
import time
from collections import deque

from starlette.responses import JSONResponse

from .config import MAX_BODY_BYTES
from .errors import AppError


class RequestGuards:
    """Bound request bodies before multipart parsing; add same-origin/security headers.

    Public API use still requires a deployment access code and edge protection for
    stronger security. Limits here are per process, not a distributed WAF.
    """
    def __init__(self, app, settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        is_api = scope["path"].startswith("/api/")
        if scope["method"] == "POST" and is_api:
            origin = headers.get(b"origin", b"").decode()
            host = headers.get(b"host", b"").decode()
            if origin and origin not in {"https://" + host, "http://" + host, self.settings.dev_origin}:
                return await JSONResponse({"error": {"code": "origin_blocked", "message": "This origin is not permitted."}}, status_code=403)(scope, receive, send)
            required = self.settings.review_access_token.get_secret_value()
            given = headers.get(b"x-review-token", b"").decode(errors="replace")
            if required and not secrets.compare_digest(required.encode(), given.encode()):
                return await JSONResponse({"error": {"code": "access_required", "message": "Enter the review access code supplied by the operator."}}, status_code=401)(scope, receive, send)
            try:
                declared = int(headers.get(b"content-length", b"0"))
                if declared < 0 or declared > MAX_BODY_BYTES:
                    raise ValueError()
            except ValueError:
                return await JSONResponse({"error": {"code": "request_too_large", "message": "The upload is too large. Use up to three images, 5 MB each."}}, status_code=413)(scope, receive, send)
            # Bounded buffer catches chunked requests even without Content-Length.
            messages, size = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                size += len(message.get("body", b""))
                if size > MAX_BODY_BYTES:
                    return await JSONResponse({"error": {"code": "request_too_large", "message": "The upload exceeds the request size limit."}}, status_code=413)(scope, receive, send)
                messages.append(message)
                if not message.get("more_body", False):
                    break
            index = 0
            async def buffered_receive():
                nonlocal index
                if index < len(messages):
                    item = messages[index]
                    index += 1
                    return item
                return await receive()
            actual_receive = buffered_receive
        else:
            actual_receive = receive
        async def guarded_send(message):
            if message["type"] == "http.response.start":
                added = [(b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"), (b"referrer-policy", b"no-referrer"), (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"), (b"content-security-policy", b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")]
                if is_api:
                    added.append((b"cache-control", b"no-store"))
                message["headers"] = list(message.get("headers", [])) + added
            await send(message)
        return await self.app(scope, actual_receive, guarded_send)


class RateLimiter:
    def __init__(self, limit: int):
        self.limit = limit
        self.hits: deque[float] = deque()

    def check(self):
        now = time.monotonic()
        while self.hits and self.hits[0] <= now - 60:
            self.hits.popleft()
        if len(self.hits) >= self.limit:
            raise AppError(429, "rate_limited", "The review service has reached its per-minute request limit. Wait and retry.", 60)
        self.hits.append(now)
