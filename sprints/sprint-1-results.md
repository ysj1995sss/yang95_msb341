# Sprint 1 results: the done line, measured

**Run:** 2026-10-03 20:24 (after Sprint 1 was turned in), model `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`
**Raw data:** `product/evals/sprint-1-alignment-results.json`. **Script:** `product/evals/run_alignment_benchmark.py`.

## The done line

> A working MVP that achieves 80% keyword and qualification alignment on 8 out of 10 real job
> postings, reduces the resume-tailoring process to under 5 minutes per application, and can be
> tested by at least 3 other job seekers who successfully generate a tailored resume without my help.

## What was run

One real resume (mine, not committed) was tailored against 10 live postings with the same pipeline
the app uses, including the Word-to-PDF step. The postings were picked by rule, not by score: two
per search title (Product Marketing Manager, Marketing Manager, Strategy Manager, Product Manager,
Operations Manager), taken alphabetically from live Greenhouse, Lever and Ashby boards, one per
company, skipping internships and postings with fewer than 3 extracted requirements.
"Alignment" is the app's score: 60% keyword match plus 40% qualification match against the posting.

| # | Company | Posting | Requirements found | Original | Tailored | 80% or more? | Bullets changed | Time |
|---|---|---|---|---|---|---|---|---|
| 1 | Affirm | [Group Product Marketing Manager](https://job-boards.greenhouse.io/affirm/jobs/8004995003) | 8 | 80% | 80% | yes | 3 | 51 s |
| 2 | Anthropic | [Product Marketing Manager, Knowledge Work - Core Products](https://job-boards.greenhouse.io/anthropic/jobs/5385651008) | 12 | 16% | 20% | no | 2 | 37 s |
| 3 | Asana | [Field Marketing Manager](https://www.asana.com/jobs/apply/8113282?gh_jid=8113282) | 7 | 92% | 92% | yes | 2 | 32 s |
| 4 | Benchling | [Product Marketing Manager](https://jobs.ashbyhq.com/benchling/874062e7-7903-4fd3-9930-ea538a4cac1e) | 13 | 92% | 92% | yes | 1 | 42 s |
| 5 | Block | [Finance & Strategy Manager](http://block.xyz/careers/jobs/5236232008?gh_jid=5236232008) | 8 | 100% | 100% | yes | 1 | 46 s |
| 6 | Brex | [Manager, CX AI Strategy](https://www.brex.com/careers/8615157002?gh_jid=8615157002) | 14 | 48% | 48% | no | 8 | 34 s |
| 7 | Cloudflare | [Senior Product Manager - Application Protection & Governance](https://boards.greenhouse.io/cloudflare/jobs/8200670?gh_jid=8200670) | 5 | 62% | 62% | no | 0 | 30 s |
| 8 | Cohere | [Product Manager,  Managed North](https://jobs.ashbyhq.com/cohere/fe2e2971-e2c0-43fd-9ab1-187571776a5d) | 11 | 52% | 52% | no | 0 | 47 s |
| 9 | Airbnb | [Customer Service Partner Operations Manager, Mandarin Speaking (Manila Based)](https://careers.airbnb.com/positions/8172735?gh_jid=8172735) | 8 | 84% | 84% | yes | 0 | 48 s |
| 10 | Coinbase | [Accounting Manager, GL Operations & Intercompany](https://www.coinbase.com/careers/positions/7822885?gh_jid=7822885) | 6 | 76% | 76% | no | 3 | 22 s |

## Result against each part of the done line

| Part | Result |
|---|---|
| 80% alignment on 8 of 10 postings | **Not met: 5 of 10 reached 80%.** |
| Under 5 minutes per application | **Met:** 22 to 51 seconds per posting (median 42 s). |
| 3 other job seekers succeed without my help | **Not met.** No one other than me has used it yet. |

## What this does and doesn't show

- **Tailoring barely moved the score.** Tailored alignment equals original alignment on 9 of 10
  postings. Edits were made (0 to 8 bullets per posting); every edit that was kept passed the truth
  checks and 4 proposed rewrites were rejected, but edits rarely added a requirement the score counts. This is a result about the metric as much
  as the tailoring: the pipeline refuses to add skills that are not in the resume.
- **Postings varied far more than tailoring did.** Scores ranged from 20% to 100%. Four of the
  six marketing and strategy postings reached 80% or more; the two product-manager postings
  scored 62% and 52%. The lowest score, Anthropic's Product Marketing Manager at 20%, is a
  marketing role, so role mismatch alone does not explain it. I did not investigate why.
- **Small and one-sided.** Ten postings, one resume, one model, one run. It was not tuned to
  reach 80%.
- **Not Sprint 1's code.** This ran on today's code. On the code that was submitted in Sprint 1,
  tailoring did not complete in the demo (no model key was set on the deployed app, and the free
  model's replies were being cut off), so this measures the pipeline as it now stands.

## Correction to the Sprint 1 retro

The retro said the definition of done was met. Measured, the speed target was met and the alignment
and user-testing targets were not. The Sprint 2 retro should say so plainly.
