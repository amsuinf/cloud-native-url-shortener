"""FastAPI URL shortener.

Endpoints
---------
POST /api/shorten      -> create a short link
GET  /{code}           -> 307 redirect to the original URL
GET  /api/links/{code} -> inspect a link without redirecting
GET  /healthz          -> liveness  (process is up)
GET  /readyz           -> readiness (Redis reachable)
GET  /metrics          -> Prometheus exposition format

The split between liveness and readiness matters in Kubernetes: a failing
readiness probe pulls the pod out of the Service endpoints (stop sending
traffic) without killing it, while a failing liveness probe restarts it.
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, HttpUrl, field_validator

from .config import settings
from .storage import RedisStore, Store, generate_code

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("url-shortener")

app = FastAPI(title="Cloud-Native URL Shortener", version="1.0.0")

# Single shared store. Swappable in tests via app.state.
store: Store = RedisStore(settings.redis_url)

# --- Prometheus metrics ---------------------------------------------------
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["endpoint"],
)
LINKS_CREATED = Counter("links_created_total", "Short links created")
REDIRECTS = Counter("redirects_total", "Successful redirects served")


@app.middleware("http")
async def observe(request: Request, call_next):
    """Record latency + request counters for every request."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    endpoint = request.url.path
    LATENCY.labels(endpoint=endpoint).observe(elapsed)
    REQUESTS.labels(
        method=request.method, endpoint=endpoint, status=response.status_code
    ).inc()
    return response


# --- Schemas ---------------------------------------------------------------
class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_code: str | None = None

    @field_validator("custom_code")
    @classmethod
    def _alnum(cls, v: str | None) -> str | None:
        if v is not None and not v.isalnum():
            raise ValueError("custom_code must be alphanumeric")
        return v


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    long_url: str


class LinkInfo(BaseModel):
    code: str
    long_url: str


# --- Routes ----------------------------------------------------------------
@app.post("/api/shorten", response_model=ShortenResponse, status_code=201)
def shorten(req: ShortenRequest) -> ShortenResponse:
    long_url = str(req.url)

    if req.custom_code:
        if store.exists(req.custom_code):
            raise HTTPException(status_code=409, detail="custom_code already taken")
        code = req.custom_code
    else:
        # Retry on the (astronomically rare) collision rather than blindly
        # overwriting an existing mapping.
        code = generate_code(settings.code_length)
        for _ in range(5):
            if not store.exists(code):
                break
            code = generate_code(settings.code_length)
        else:
            raise HTTPException(status_code=500, detail="could not allocate code")

    store.save(code, long_url, settings.link_ttl_seconds)
    LINKS_CREATED.inc()
    log.info("created code=%s -> %s", code, long_url)
    return ShortenResponse(
        code=code,
        short_url=f"{settings.base_url.rstrip('/')}/{code}",
        long_url=long_url,
    )


@app.get("/api/links/{code}", response_model=LinkInfo)
def link_info(code: str) -> LinkInfo:
    url = store.lookup(code)
    if url is None:
        raise HTTPException(status_code=404, detail="not found")
    return LinkInfo(code=code, long_url=url)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness: the process can serve requests."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> Response:
    """Readiness: dependencies (Redis) are reachable."""
    if store.ping():
        return Response(content='{"status":"ready"}', media_type="application/json")
    return Response(
        content='{"status":"degraded"}',
        media_type="application/json",
        status_code=503,
    )


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# NOTE: this catch-all redirect MUST be declared last. FastAPI/Starlette match
# routes in definition order, so a "/{code}" above would otherwise swallow
# /healthz, /readyz, /metrics, etc.
@app.get("/{code}")
def redirect(code: str):
    url = store.lookup(code)
    if url is None:
        raise HTTPException(status_code=404, detail="not found")
    REDIRECTS.inc()
    # 307 preserves method + is non-cacheable by default, so analytics stay
    # accurate and we keep control of the mapping.
    return RedirectResponse(url=url, status_code=307)
