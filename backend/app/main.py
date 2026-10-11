"""EMS API service (FastAPI). Run: FORWARDED_ALLOW_IPS=<load balancer range> uvicorn app.main:app --proxy-headers"""
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import health
from app.auth import google
from app.auth import router as auth
from app.config import Settings, get_settings
from app.crm import router as crm
from app.dashboards import router as dashboards
from app.finance import router as finance
from app.graph import router as graph
from app.hr import router as hr
from app.org import router as org
from app.platform import notifications
from app.platform.db import make_engine
from app.platform.web import RequestMiddleware, configure_logging, install_exception_handlers
from app.projects import router as projects
from app.room import router as room

ROUTERS = [health.router, auth.router, google.router, org.router, room.router, hr.router, projects.router, crm.router,
           finance.router, graph.router, dashboards.router, notifications.router]


def _csp(settings: Settings) -> str:
    connect = ["'self'"]
    if settings.livekit_url:
        u = urlparse(settings.livekit_url)
        connect.append(f"{u.scheme}://{u.netloc}")
    return f"default-src 'none'; connect-src {' '.join(connect)}; frame-ancestors 'none'"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="EMS API", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    install_exception_handlers(app)
    for r in ROUTERS:
        app.include_router(r)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                       allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "X-Org-Id", "Idempotency-Key"])
    app.add_middleware(RequestMiddleware, csp=_csp(settings), hsts=settings.app_base_url.startswith("https://"))
    return app


def __getattr__(name: str):
    # `uvicorn app.main:app` builds the app on first access, so importing this module never needs the environment.
    if name == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError(name)
