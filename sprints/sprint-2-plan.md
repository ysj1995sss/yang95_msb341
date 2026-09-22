# Sprint 2 Plan

**Goal:** Close out Sprint 1: turn the job-copilot-workflow.html roadmap's "✓ Built" status for steps 1, 2, and 10–20 from a claim into something actually true, by finishing every partially-complete piece (original resume preservation, candidate fit score, unsupported-claims reporting, resume-design preservation) and fixing the real-world bugs a live test surfaces — before Sprint 2+ moves on to the job search and discovery work (steps 3–9) the roadmap has planned next.

**Why this:** It is because I need to complete the project and test it in real world and get real user feedbacks. The workflow diagram marks every Sprint 1 step as "✓ Built," but running the actual pipeline against my own real resume and a real job posting this week proved that wasn't true yet — the parser lost real content, the job analyzer returned a completely empty gap report on a real posting, and the system almost let a fabricated claim through undetected. None of that shows up until you use real data instead of test fixtures. Closing those gaps now, honestly, is what makes the rest of the roadmap (job search, auto-apply) worth building on top of — there's no point scouting real jobs in Sprint 2+ if the tailoring underneath still breaks on a real resume.

**Done looks like:** A user can upload a resume and paste a real job description, get a tailored resume that reaches 85%+ alignment when they're a genuine match for the role (or an honest report of the ceiling and what's missing when they're not), export it as a validated PDF — and at least 2 real people other than me can do this themselves without my help.

**Predicted difficulty:** 4
