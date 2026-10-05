from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(title="Resume Copilot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    apply_additive_migrations(engine)


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


@app.get("/health")
def health():
    return {"status": "ok"}
