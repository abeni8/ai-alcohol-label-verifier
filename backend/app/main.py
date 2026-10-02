import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from .config import MAX_IMAGE_BYTES, MAX_IMAGES, ROOT, Settings
from .errors import AppError
from .images import prepare_image
from .models import Application, Verification
from .policy import LIMITATIONS, POLICY_VERSION, WARNING
from .providers import DemoExtractor, OpenAIExtractor
from .security import RateLimiter, RequestGuards
from .validation import validate, warning_diff


def create_app(settings: Settings | None = None, extractor=None) -> FastAPI:
    settings = settings or Settings()
    @asynccontextmanager
    async def lifespan(app):
        async with httpx.AsyncClient(follow_redirects=False) as client:
            app.state.extractor = extractor or (DemoExtractor() if settings.provider == "demo" else OpenAIExtractor(settings, client))
            app.state.capacity = asyncio.Semaphore(settings.max_concurrent_requests)
            app.state.limiter = RateLimiter(settings.requests_per_minute)
            yield
    app = FastAPI(title="Label Review API", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.add_middleware(RequestGuards, settings=settings)

    @app.exception_handler(AppError)
    async def app_error(request, exc):
        return JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status, headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else None)

    @app.exception_handler(RequestValidationError)
    async def request_error(request, exc):
        # Do not echo input values, tokens, documents, or the raw request body.
        return JSONResponse({"error": {"code": "invalid_request", "message": "Check the request fields and provide the required files."}}, status_code=422)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/ready")
    async def ready():
        return JSONResponse({"ready": settings.ready, "mode": settings.provider}, status_code=200 if settings.ready else 503)

    @app.get("/api/config")
    async def config():
        return {"mode": settings.provider, "ready": settings.ready, "requires_access_code": bool(settings.review_access_token.get_secret_value()), "max_images": MAX_IMAGES, "max_image_bytes": MAX_IMAGE_BYTES, "max_batch_rows": 300, "target_ms": 5000, "warning": WARNING, "policy_version": POLICY_VERSION}

    @app.get("/api/samples")
    async def samples():
        return json.loads((ROOT / "samples" / "catalog.json").read_text())

    @app.get("/api/sample-files/{filename}")
    async def sample_file(filename: str):
        if not filename or '/' in filename or '\\' in filename or filename.startswith('.') or (ROOT / "samples" / filename).suffix.lower() not in {".png", ".jpg", ".jpeg", ".csv"}:
            raise AppError(404, "not_found", "Sample file not found.")
        path = ROOT / "samples" / filename
        if not path.is_file():
            raise AppError(404, "not_found", "Sample file not found.")
        return FileResponse(path, filename=filename)

    @app.post("/api/verify", response_model=Verification)
    async def verify(request: Request, application: Annotated[str, Form()], images: Annotated[list[UploadFile], File()]):
        start = time.perf_counter()
        try:
            if len(application) > 12000:
                raise AppError(422, "application_too_large", "Application fields exceed the permitted size.")
            try:
                expected = Application.model_validate_json(application)
            except ValidationError as exc:
                messages = [f"{'.'.join(map(str, e['loc'])) or 'Application'}: {e['msg']}" for e in exc.errors(include_input=False, include_context=False)]
                raise AppError(422, "invalid_application", " ".join(messages)) from exc
            if not 1 <= len(images) <= MAX_IMAGES:
                raise AppError(422, "image_count", "Upload between one and three label images per application.")
            names = [f.filename for f in images]
            if len(names) != len(set(names)):
                raise AppError(422, "duplicate_images", "Image filenames must be unique within an application.")
            request.app.state.limiter.check()
            try:
                await asyncio.wait_for(request.app.state.capacity.acquire(), timeout=1)
            except TimeoutError as exc:
                raise AppError(429, "service_busy", "All review slots are busy. Wait a moment and retry.", 2) from exc
            try:
                async with asyncio.timeout(settings.ai_timeout_seconds + 4):
                    prepared = []
                    for upload in images:
                        raw = await upload.read(MAX_IMAGE_BYTES + 1)
                        prepared.append(await run_in_threadpool(prepare_image, upload.filename or "", upload.content_type or "", raw))
                    if await request.is_disconnected():
                        raise AppError(499, "cancelled", "The request was cancelled.")
                    extraction_start = time.perf_counter()
                    extracted = await request.app.state.extractor.extract(prepared)
                    extraction_ms = (time.perf_counter() - extraction_start) * 1000
                    checks = validate(expected, extracted)
                    elapsed = round((time.perf_counter() - start) * 1000, 1)
                    return Verification(application_id=expected.application_id, mode=settings.provider, model=settings.openai_model if settings.provider == "openai" else "synthetic-fixtures", checks=checks, matches=sum(c.status == "match" for c in checks), reviews=sum(c.status == "review" for c in checks), not_checked=sum(c.status == "not_checked" for c in checks), elapsed_ms=elapsed, extraction_ms=round(extraction_ms, 1), target_met=elapsed <= 5000 if settings.provider == "openai" else None, issues=extracted.issues + (["Images larger than 3000 pixels on an edge were downscaled; submit a separate readable warning crop when needed."] if any(p.resized for p in prepared) else []), filenames=[p.filename for p in prepared], policy_version=POLICY_VERSION, warning_diff=warning_diff(extracted.warning.value or ""), limitations=LIMITATIONS)
            except TimeoutError as exc:
                raise AppError(504, "verification_timeout", "Verification timed out. No successful decision was returned; retry or review manually.") from exc
            finally:
                request.app.state.capacity.release()
        finally:
            for upload in images:
                await upload.close()

    from .batch import register_batch_routes
    register_batch_routes(app)
    static = ROOT / "frontend" / "dist"
    if static.is_dir():
        app.mount("/", StaticFiles(directory=static, html=True), name="frontend")
    return app


app = create_app()
