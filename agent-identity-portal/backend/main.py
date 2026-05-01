"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from database import init_db
from routers import blueprints, identities, permissions, approvals, admin

logger = logging.getLogger("main")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        from seed import seed_if_empty
        seed_if_empty()
    except Exception as exc:
        logger.warning("Startup init failed (will retry on first request): %s", exc)
    logger.info("Agent Identity Portal started - provisioning mode: %s", settings.provisioning_mode)
    yield


# Disable OpenAPI spec in production (set ENABLE_DOCS=true to enable)
import os
_enable_docs = os.getenv("ENABLE_DOCS", "false").lower() in ("1", "true", "yes")

app = FastAPI(
    title="Agent Identity Portal",
    description="Self-service portal for requesting Agent Blueprints, Identities, and Permissions",
    version="0.1.0",
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    openapi_url="/openapi.json" if _enable_docs else None,
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)

# Parse comma-separated origins to support multiple deployment envs.
_origins = [o.strip() for o in settings.frontend_origin.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(blueprints.router)
app.include_router(identities.router)
app.include_router(permissions.router)
app.include_router(approvals.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": settings.provisioning_mode}
