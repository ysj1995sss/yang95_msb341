"""Career Profile (spec 009 phase 1): the same store, provenance and review rules as the
Streamlit Career Profile page. Legally significant answers are only what the user chose."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.workspace.context import Workspace, jsonable, workspace

router = APIRouter(prefix="/v2", tags=["workspace"])

MAX_RESUME_BYTES = 10 * 1024 * 1024


def _lines(values: list[str]) -> list[str]:
    return [v.strip() for v in values or [] if v and v.strip()]


def _view(ws: Workspace) -> dict:
    from resume_tailorer.job_search.job_attributes import EXPERIENCE_LEVEL_OPTIONS, INDUSTRY_OPTIONS
    from resume_tailorer.profile_store import EDITED
    from resume_tailorer.ui.onboarding import WIZARD_STEPS, goals_summary, suggested_titles
    from resume_tailorer.ui.profile_readiness import (
        build_readiness, first_section_needing_review, provenance_summary, section_rows,
    )

    record = ws.record
    readiness = build_readiness(record)
    answers = ws.service.applications_db.get_answer_entries()
    rows = section_rows(record, len(answers))
    profile = record.get("profile") or {}
    return {
        "readiness": {**jsonable(readiness), "summary": readiness.summary},
        "rows": jsonable(rows),
        "first_to_review": first_section_needing_review(rows),
        "attention": [issue for r in rows for issue in r.issues],
        "provenance": {r.key: provenance_summary(record, r.key) for r in rows},
        "edited": sorted(p for p, s in (record.get("provenance") or {}).items() if s == EDITED),
        "profile": profile,
        "links": record.get("links") or {},
        "preferences": record.get("preferences") or {},
        "authorization": record.get("authorization") or {},
        "no_education": bool(record.get("no_education")),
        "resume": record.get("resume"),
        "resume_versions": len(record.get("resume_history") or []),
        "facts_confirmed_at": record.get("facts_confirmed_at"),
        "answers": answers,
        "goals_summary": [{"label": k, "value": v} for k, v in goals_summary(record)],
        "goal_options": {
            "steps": jsonable(WIZARD_STEPS),
            "suggested_titles": suggested_titles(profile),
            "experience_levels": EXPERIENCE_LEVEL_OPTIONS,
            "industries": INDUSTRY_OPTIONS,
            "work_modes": [{"value": "any", "label": "No preference"}, {"value": "remote", "label": "Remote"},
                           {"value": "hybrid", "label": "Hybrid"}, {"value": "onsite", "label": "On-site"}],
        },
    }


@router.get("/profile")
def get_profile(ws: Workspace = Depends(workspace)):
    return _view(ws)


@router.post("/profile/resume")
async def import_resume_file(file: UploadFile = File(...), ws: Workspace = Depends(workspace)):
    from resume_tailorer.profile_import import import_resume

    name = file.filename or "resume"
    if not name.lower().endswith((".docx", ".pdf")):
        raise HTTPException(400, "Upload a Word (.docx) or PDF resume.")
    data = await file.read()
    if not data or len(data) > MAX_RESUME_BYTES:
        raise HTTPException(400, "That file is empty or larger than 10 MB.")
    try:
        import_resume(ws.store(), name, data)
    except Exception as exc:
        raise HTTPException(422, f"We couldn't read that file: {exc}. Try the Word version, or a PDF with "
                                 "selectable text.") from exc
    return _view(Workspace(ws.owner))


class Contact(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""


class Summary(BaseModel):
    summary: str = ""


class Role(BaseModel):
    index: int
    title: str = ""
    employer: str = ""
    dates: str = ""
    bullets: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: str = ""
    field: str = ""
    institution: str = ""
    year: Optional[int] = None
    gpa: Optional[str] = None


class Education(BaseModel):
    entries: list[EducationEntry] = Field(default_factory=list)
    no_education: bool = False


class Skills(BaseModel):
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class Certifications(BaseModel):
    certifications: list[str] = Field(default_factory=list)


class Links(BaseModel):
    linkedin: str = ""
    portfolio: str = ""
    github: str = ""


class Authorization(BaseModel):
    authorized_to_work: Optional[bool] = None
    sponsorship_required: Optional[bool] = None


class Goals(BaseModel):
    job_title: str
    location: str = ""
    relocation_willing: bool = False
    remote_preference: str = "any"
    experience_level: list[str] = Field(default_factory=list)
    min_salary: int = 0
    industries: list[str] = Field(default_factory=list)
    authorized_to_work: Optional[bool] = None
    sponsorship_required: Optional[bool] = None
    weekly_goal: Optional[int] = None


def _save_profile(ws: Workspace, new_profile: dict, **extra) -> dict:
    from resume_tailorer.profile_store import apply_edits

    record = ws.record
    changed = apply_edits(record, new_profile)
    record.update(extra)
    ws.save_record(record)
    return {"changed": len(changed), **_view(ws)}


def _profile(ws: Workspace) -> dict:
    if not ws.record.get("profile"):
        raise HTTPException(409, "Import your resume first.")
    return dict(ws.record["profile"])


@router.put("/profile/contact")
def save_contact(body: Contact, ws: Workspace = Depends(workspace)):
    profile = _profile(ws)
    contact = {**(profile.get("contact_info") or {}), **{k: v.strip() for k, v in body.model_dump().items()}}
    return _save_profile(ws, {**profile, "contact_info": contact})


@router.put("/profile/summary")
def save_summary(body: Summary, ws: Workspace = Depends(workspace)):
    return _save_profile(ws, {**_profile(ws), "summary": body.summary.strip()})


@router.put("/profile/work")
def save_role(body: Role, ws: Workspace = Depends(workspace)):
    from resume_tailorer.profile_store import split_bullets

    profile = _profile(ws)
    jobs = list(profile.get("work_experience") or [])
    if not 0 <= body.index < len(jobs):
        raise HTTPException(404, "That role isn't in your profile.")
    job = jobs[body.index]
    responsibilities, accomplishments = split_bullets(job, _lines(body.bullets))
    jobs[body.index] = {**job, "title": body.title.strip(), "employer": body.employer.strip(),
                        "dates": body.dates.strip(), "responsibilities": responsibilities,
                        "accomplishments": accomplishments}
    return _save_profile(ws, {**profile, "work_experience": jobs})


@router.put("/profile/education")
def save_education(body: Education, ws: Workspace = Depends(workspace)):
    profile = _profile(ws)
    old = list(profile.get("education") or [])
    entries = []
    for i, entry in enumerate(body.entries):
        base = old[i] if i < len(old) else {"notes": []}
        entries.append({**base, "degree": entry.degree.strip(), "field": entry.field.strip(),
                        "institution": entry.institution.strip(), "year": entry.year or 0,
                        "gpa": (entry.gpa or "").strip() or None})
    return _save_profile(ws, {**profile, "education": entries}, no_education=body.no_education)


@router.put("/profile/skills")
def save_skills(body: Skills, ws: Workspace = Depends(workspace)):
    return _save_profile(ws, {**_profile(ws), "skills": list(dict.fromkeys(_lines(body.skills))),
                              "tools": list(dict.fromkeys(_lines(body.tools)))})


@router.put("/profile/certifications")
def save_certifications(body: Certifications, ws: Workspace = Depends(workspace)):
    return _save_profile(ws, {**_profile(ws), "certifications": _lines(body.certifications)})


@router.put("/profile/links")
def save_links(body: Links, ws: Workspace = Depends(workspace)):
    record = ws.record
    record["links"] = {k: v.strip() for k, v in body.model_dump().items()}
    ws.save_record(record)
    return _view(ws)


@router.put("/profile/authorization")
def save_authorization(body: Authorization, ws: Workspace = Depends(workspace)):
    record = ws.record
    record["authorization"] = {**(record.get("authorization") or {}), **body.model_dump()}
    ws.save_record(record)
    return _view(ws)


@router.put("/profile/goals")
def save_goals_endpoint(body: Goals, ws: Workspace = Depends(workspace)):
    from resume_tailorer.ui.onboarding import save_goals

    if not body.job_title.strip():
        raise HTTPException(400, "Add the role you're looking for.")
    record = ws.record
    goals: dict[str, Any] = body.model_dump()
    goals["job_title"] = body.job_title.strip()
    weekly_goal = goals.pop("weekly_goal")
    save_goals(record, goals)
    if weekly_goal is not None:
        record["preferences"]["weekly_goal"] = max(0, int(weekly_goal))
    ws.save_record(record)
    return _view(ws)


@router.post("/profile/confirm")
def confirm_rest(ws: Workspace = Depends(workspace)):
    from resume_tailorer.profile_store import confirm_remaining

    record = ws.record
    if not record.get("profile"):
        raise HTTPException(409, "Import your resume first.")
    count = confirm_remaining(record)
    ws.save_record(record)
    return {"confirmed": count, **_view(ws)}


class Answer(BaseModel):
    question: str
    answer: str


@router.post("/answers")
def save_answer(body: Answer, ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.answer_bank import question_key

    if not body.question.strip() or not body.answer.strip():
        raise HTTPException(400, "Write both the question and your answer.")
    ws.service.applications_db.save_answer(question_key(body.question), body.question.strip(), body.answer.strip())
    return {"answers": ws.service.applications_db.get_answer_entries()}


@router.delete("/answers/{key}")
def delete_answer(key: str, ws: Workspace = Depends(workspace)):
    ws.service.applications_db.delete_answer(key)
    return {"answers": ws.service.applications_db.get_answer_entries()}
