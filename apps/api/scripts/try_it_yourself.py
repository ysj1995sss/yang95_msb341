"""
Try It Yourself: exercises the real product end to end -- register, upload
your actual resume, tailor it against a real job description, save the
tailored PDF -- without touching Swagger UI or writing any API calls
yourself.

Prerequisites:
  1. The API server is running: uvicorn app.main:app --reload
  2. apps/api/.env has LLM_MODEL and LLM_API_KEY set

Usage (from apps/api, with the venv activated):
    python scripts/try_it_yourself.py --resume "C:\\path\\to\\your_resume.pdf" --job job_description.txt

If you don't have a job description saved yet: open Notepad, paste in a real
job posting's text, save it as job_description.txt, then point --job at it.
"""

import argparse
import base64
import sys

# Some Windows consoles default to a non-UTF-8 codepage (e.g. GBK) that
# can't encode common symbols like the warning sign used below -- found
# live (2026-09-22): the script crashed with UnicodeEncodeError right when
# it had something important to show (unsupported claims added), losing
# the whole report. Force UTF-8 on stdout/stderr so this can never crash
# on output again, regardless of the console's codepage.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Python < 3.7 or a stream that doesn't support reconfigure.
from pathlib import Path

import httpx

API_BASE = "http://localhost:8000"


def main():
    parser = argparse.ArgumentParser(description="Register, upload your resume, and tailor it against a real job.")
    parser.add_argument("--resume", required=True, help="Path to your resume PDF or DOCX")
    parser.add_argument("--job", required=True, help="Path to a .txt file containing the job description")
    parser.add_argument("--email", default="me@example.com", help="Reused across runs to keep the same profile")
    parser.add_argument("--password", default="testpassword123")
    parser.add_argument("--out", default="tailored_resume.pdf", help="Where to save the tailored PDF")
    parser.add_argument("--length", default="1_page", choices=["1_page", "2_page", "preserve"])
    parser.add_argument(
        "--conservative",
        action="store_true",
        help="Only insert missing ATS keywords into existing bullets, don't rewrite them",
    )
    args = parser.parse_args()

    resume_path = Path(args.resume)
    job_path = Path(args.job)
    if not resume_path.exists():
        sys.exit(f"Resume file not found: {resume_path}")
    if not job_path.exists():
        sys.exit(f"Job description file not found: {job_path}")

    job_description = job_path.read_text(encoding="utf-8")

    try:
        with httpx.Client(base_url=API_BASE, timeout=120.0) as client:
            print("1. Logging in (registering on first run)...")
            r = client.post("/auth/register", json={"email": args.email, "password": args.password})
            if r.status_code == 409:
                r = client.post("/auth/login", json={"email": args.email, "password": args.password})
            r.raise_for_status()
            token = r.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("   OK")

            print(f"2. Uploading your resume ({resume_path.name})...")
            with open(resume_path, "rb") as f:
                r = client.post("/profile/upload", files={"file": (resume_path.name, f)}, headers=headers)
            r.raise_for_status()
            profile = r.json()
            print(f"   Parsed name: {profile['contact_info'].get('name', 'Unknown')}")
            print(f"   Skills found: {profile['skills']}")
            print(f"   Work history entries: {len(profile['work_experience'])}")
            if not profile["skills"] and not profile["work_experience"]:
                print(
                    "   WARNING: the parser found almost nothing usable. It works best with"
                    " clear section headings ('EXPERIENCE', 'SKILLS', 'EDUCATION') -- check"
                    " your resume's formatting if this looks empty."
                )

            print("3. Tailoring against the job description (real LLM call, ~10-30s)...")
            r = client.post(
                "/tailor/preview",
                json={
                    "job_description": job_description,
                    "generate_pdf": True,
                    "target_length": args.length,
                    "conservative": args.conservative,
                },
                headers=headers,
            )
    except httpx.ConnectError:
        sys.exit(
            "Could not reach the API at "
            f"{API_BASE}. Is uvicorn running? (uvicorn app.main:app --reload from apps/api)"
        )

    if r.status_code == 503:
        sys.exit(
            f"LLM not configured: {r.json()['detail']}\n"
            "Set LLM_MODEL and LLM_API_KEY in apps/api/.env, then restart the server."
        )
    if r.status_code == 400:
        sys.exit(f"Request rejected: {r.json()['detail']}")
    r.raise_for_status()
    result = r.json()

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Original resume match:   {result['original_match_score']:.0%}")
    print(f"  Tailored resume match:   {result['final_score']:.0%}")
    if result.get("candidate_fit_score") is not None:
        print(f"  Candidate fit score:     {result['candidate_fit_score']:.0f}/100")
    print(f"  Optimization iterations: {result['iterations']}")
    print(f"  {result['gap_summary']}")

    if result.get("bullets_evaluated"):
        print(
            f"  Bullets: {result['bullets_evaluated']} evaluated, {result['bullets_changed']} changed, "
            f"{result['bullets_rejected']} rejected by a safety check "
            f"({result['addressable_requirements']} job requirements had real evidence in the resume)"
        )
        if result.get("tailoring_seems_shallow"):
            print("  ⚠ Tailoring may be too shallow -- see bullet warnings below.")

    if result["unsupported_claims_added"]:
        print("\n  \u26a0 REVIEW BEFORE USING -- the system could not verify these against your profile:")
        for claim in result["unsupported_claims_added"]:
            print(f"    - {claim}")

    if result["fabrication_risk_issues"]:
        print("\n  \u26a0 Fabrication risk flags:")
        for issue in result["fabrication_risk_issues"]:
            print(f"    - {issue}")

    if result.get("docx_base64"):
        docx_out = Path(args.out).with_suffix(".docx")
        docx_out.write_bytes(base64.b64decode(result["docx_base64"]))
        print(f"\n  Tailored DOCX saved to: {docx_out.resolve()}")
        print("  (Your original resume, tailored bullets spliced in place -- same fonts/margins/layout.)")
        if result.get("page_count_preserved") is False:
            print(
                f"  WARNING: page count changed ({result.get('original_page_count')} -> "
                f"{result.get('tailored_page_count')} pages)"
            )
        elif result.get("docx_conversion_available") is False:
            print("  NOTE: docx2pdf/Word not available on this machine -- page count could not be verified.")
        if result.get("bullet_warnings"):
            print("  Bullet warnings:")
            for w in result["bullet_warnings"]:
                print(f"    - {w}")

    if result.get("pdf_base64"):
        out_path = Path(args.out)
        out_path.write_bytes(base64.b64decode(result["pdf_base64"]))
        print(f"\n  Tailored PDF saved to: {out_path.resolve()}")
        print("  Open it and read it the way a hiring manager would.")
    elif not result.get("docx_base64"):
        print(f"\n  PDF generation did not produce a usable file. Issues: {result.get('pdf_issues')}")


if __name__ == "__main__":
    main()
