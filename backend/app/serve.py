"""API entry point: python -m app.serve

Validates the configuration first (app/config.py), then runs uvicorn with proxy headers trusted only from
FORWARDED_ALLOW_IPS. Without it uvicorn trusts just 127.0.0.1, every request looks like it comes from the load
balancer, and the per-IP rate limits (login, sign-up) apply to all users at once.
"""
import os

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run("app.main:app", host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "8000")),  # noqa: S104 - container
                proxy_headers=True, forwarded_allow_ips=settings.forwarded_allow_ips)


if __name__ == "__main__":
    main()
