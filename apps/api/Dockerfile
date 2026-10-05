# The workspace API for the web app (spec 009). Build from the repository root:
#   docker build -f apps/api/Dockerfile -t job-copilot-api .
FROM python:3.14-slim

# LibreOffice and metric-compatible fonts: Word resumes become PDFs on Linux (decision 027).
COPY packages.txt /tmp/packages.txt
RUN apt-get update \
    && xargs -a /tmp/packages.txt apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY product/requirements.txt product/requirements.txt
RUN pip install --no-cache-dir -r product/requirements.txt
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/api/app apps/api/app
RUN pip install --no-cache-dir ./apps/api
COPY product/resume_tailorer product/resume_tailorer

# Per-user data lives on a mounted disk at /data. The older password-login routes are off:
# the web app uses only /v2, so no database is needed.
ENV PYTHONPATH=/srv/product:/srv/apps/api \
    JOB_COPILOT_DATA_DIR=/data \
    APP_ENV=production \
    LEGACY_ROUTES=false
WORKDIR /srv/apps/api
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
