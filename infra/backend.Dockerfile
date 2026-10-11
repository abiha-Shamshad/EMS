# One image for the API and the worker (DEC-001). Build from the repository root:
#   docker build -f infra/backend.Dockerfile -t ems-backend .
# API:     docker run ... ems-backend
# Worker:  docker run ... ems-backend python -m worker.main
# Migrate: docker run -e ADMIN_DATABASE_URL=... ems-backend alembic upgrade head
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 ems
WORKDIR /srv/ems/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY db /srv/ems/db
COPY backend/app ./app
COPY backend/worker ./worker
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./

USER ems
EXPOSE 8000
# Client IPs (used by rate limits) come from X-Forwarded-For only when the request arrives from a trusted proxy.
# Set FORWARDED_ALLOW_IPS to the load balancer's address range; uvicorn's default trusts only 127.0.0.1.
# Never use "*": any client could then spoof its IP and bypass the per-IP limits.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
