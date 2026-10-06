import logging
import sys
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app import alerts
from app.config import get_settings
from app.db import Base, engine
from app import models  # noqa: F401
from app.migrations import apply_additive_migrations
from app.auth.router import router as auth_router
from app.profile.router import router as profile_router
from app.goals.router import router as goals_router
from app.job_search_profiles.router import router as job_search_profiles_router
from app.jobs.router import router as jobs_router
from app.devices.router import router as devices_router
from app.tailor.router import router as tailor_router
from app.workspace.home_router import router as workspace_home_router
from app.workspace.profile_router import router as workspace_profile_router
from app.workspace.jobs_router import router as workspace_jobs_router
from app.workspace.tailor_router import router as workspace_tailor_router
from app.workspace.apply_router import router as workspace_apply_router
from app.workspace.tracker_router import router as workspace_tracker_router
from app.workspace.account_router import router as workspace_account_router
from app.workspace.gmail_router import router as workspace_gmail_router
from app.workspace.batch_router import router as workspace_batch_router

app = FastAPI(title="Resume Copilot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_LEGACY = get_settings().legacy_routes


@app.on_event("startup")
def on_startup():
    if _LEGACY:
        Base.metadata.create_all(bind=engine)
        apply_additive_migrations(engine)


if _LEGACY:
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(goals_router)
    app.include_router(job_search_profiles_router)
    app.include_router(jobs_router)
    app.include_router(devices_router)
    app.include_router(tailor_router)
# Spec 009: the workspace API the Next.js frontend uses (shared with the Streamlit app's data).
app.include_router(workspace_home_router)
app.include_router(workspace_profile_router)
app.include_router(workspace_jobs_router)
app.include_router(workspace_tailor_router)
app.include_router(workspace_apply_router)
app.include_router(workspace_tracker_router)
app.include_router(workspace_account_router)
app.include_router(workspace_gmail_router)
app.include_router(workspace_batch_router)


logger = logging.getLogger("job_copilot.api")
if not logging.getLogger().handlers:  # the host captures stdout/stderr (e.g. Render's log stream)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@app.middleware("http")
async def request_log(request: Request, call_next):
    """One line per request, and every unexpected error logged with a reference the user sees
    (the host's logs, e.g. Render's, are where failures show up; decision 030)."""
    reference = uuid.uuid4().hex[:10]
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error %s on %s %s", reference, request.method, request.url.path)
        alerts.notify(reference, f"{request.method} {request.url.path}", type(sys.exc_info()[1]).__name__)
        return JSONResponse(status_code=500, content={
            "detail": f"Something went wrong on our side. If it keeps happening, mention reference {reference}."})
    if response.status_code >= 500:
        logger.error("%s %s -> %s (%s)", request.method, request.url.path, response.status_code, reference)
        alerts.notify(reference, f"{request.method} {request.url.path}", f"HTTP {response.status_code}")
    else:
        logger.info("%s %s -> %s in %.0f ms", request.method, request.url.path, response.status_code,
                    (time.perf_counter() - started) * 1000)
    response.headers["X-Request-Id"] = reference
    return response


@app.get("/health")
def health():
    return {"status": "ok"}
