"""Sprint 1 done-line check: tailor one resume against 10 live postings and record
alignment and time for each.

Usage (from product/):  python evals/run_alignment_benchmark.py <resume.docx> <out_dir>
"""
import json, sys, time, datetime
sys.path.insert(0, ".")  # run from product/
from dotenv import load_dotenv
load_dotenv(".env")
from resume_tailorer.job_search.scrapers import GreenhouseScraper, AshbyScraper, LeverScraper
from resume_tailorer.job_search.ui_helpers import build_search_goals_from_form as g
from resume_tailorer.parsers import ResumeParser
from resume_tailorer.analyzers import JobAnalyzer, ResumeBenchmarker, GapAnalyzer
from resume_tailorer.llm.settings import resolve_settings
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer
from resume_tailorer.tailorer.optimizer import ResumeTailoringOptimizer
from resume_tailorer.docx_export import run_docx_tailoring_pipeline

OUT = sys.argv[2]      # folder for the results JSON
RESUME = sys.argv[1]   # path to the resume (.docx); never committed
TITLES = ["Product Marketing Manager", "Marketing Manager", "Strategy Manager", "Product Manager", "Operations Manager"]

# 1. choose 10 live postings: 2 per title, different companies, with real requirements
chosen, seen = [], set()
scrapers = [GreenhouseScraper(), AshbyScraper(), LeverScraper()]
for title in TITLES:
    goals = g({"job_title": title, "max_salary": 0})
    pool = [j for s in scrapers for j in s.scrape(goals)]
    pool.sort(key=lambda j: (j.company, j.title))
    taken = 0
    for j in pool:
        if j.company in seen or "intern" in j.title.lower():
            continue
        a = JobAnalyzer().analyze(j.description)
        if len(a.required_qualifications) < 3:
            continue
        chosen.append((title, j)); seen.add(j.company); taken += 1
        if taken == 2:
            break
print("chosen", len(chosen), flush=True)

profile = ResumeParser().parse(RESUME)
docx_bytes = open(RESUME, "rb").read()
llm = LLMClient(resolve_settings())
results = []
for query, job in chosen[:10]:
    row = {"query": query, "company": job.company, "title": job.title, "url": job.url, "source": job.source.value}
    t0 = time.time()
    try:
        ja = JobAnalyzer().analyze(job.description)
        bm = ResumeBenchmarker().benchmark(profile, ja)
        gr = GapAnalyzer().analyze(profile, ja, bm)
        res = run_docx_tailoring_pipeline(docx_bytes, profile, ja, gr,
                                          bullet_tailorer=DocxBulletTailorer(llm=llm), convert_to_pdf=True)
        tailored, _m, _x = ResumeTailoringOptimizer._score_resume(res.tailored_scoring_text, ja, profile)
        row.update(requirements=len(ja.required_qualifications) + len(ja.preferred_qualifications),
                   original_alignment=round(bm.original_match_score * 100, 1),
                   tailored_alignment=round(tailored * 100, 1),
                   bullets_changed=res.bullets_changed, bullets_rejected=res.bullets_rejected,
                   validation=res.validation.status.value, pages=f"{res.original_page_count}->{res.tailored_page_count}",
                   error=None)
    except Exception as exc:
        row.update(error=str(exc)[:200])
    row["seconds"] = round(time.time() - t0)
    results.append(row)
    print(json.dumps(row), flush=True)
    json.dump({"ran_at": datetime.datetime.now().isoformat(timespec="minutes"), "model": llm.settings.model, "rows": results},
              open(OUT + "/bench10.json", "w"), indent=1)
print("DONE", flush=True)
