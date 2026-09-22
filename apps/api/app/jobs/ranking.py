def _norm(s: str) -> str:
    return (s or "").strip().lower()


def is_excluded_by_goals(job: dict, goals: dict | None) -> bool:
    if not goals:
        return False
    company = _norm(job.get("company") or "")
    for exc in goals.get("exclude_companies") or []:
        if _norm(exc) == company:
            return True
    return False


def _title_matches(goal_title: str, job_title: str) -> bool:
    g = _norm(goal_title)
    j = _norm(job_title)
    if not g or not j:
        return False
    return g in j or j in g


def apply_goals_rank_boost(score: float, job: dict, goals: dict | None) -> float:
    if not goals:
        return score
    if is_excluded_by_goals(job, goals):
        return 0.0

    adjusted = score
    titles = goals.get("titles") or []
    if titles:
        job_title = job.get("title") or ""
        if any(_title_matches(t, job_title) for t in titles):
            adjusted += 10.0

    pref = goals.get("sponsorship_preference") or "show_all"
    sponsorship = _norm(job.get("sponsorship") or "unknown")
    if pref == "none_needed" and sponsorship == "yes":
        adjusted -= 15.0

    return max(0.0, min(100.0, adjusted))
