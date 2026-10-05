# Decision 031: Tailor with your own ChatGPT plan through the Codex CLI (local only)

**Date:** 2026-10-05
**Status:** Active. The builder asked to power the website's model calls with their ChatGPT
plan's weekly Codex allowance instead of a paid API key.

## What

A model named `codex-cli` (or `codex-cli/<model>` to pick a Codex model) in
`resume_tailorer/llm/client.py`. Each model call runs one `codex exec` with the Codex CLI that
is signed in with the person's ChatGPT account:

- **Isolated:** each call runs in a throwaway empty folder, in a read-only sandbox, with
  `--ephemeral` (no saved session) and `--ignore-rules`.
- **Plain answers:** the prompt tells Codex to act as a plain text-completion service and not
  to run commands or touch files.
- **Fast:** reasoning effort is set to low.
- **No key:** no API key is needed. `resolve_settings` accepts `codex-cli` without one.
- **Plain errors:** a missing CLI, a used-up plan or a signed-out CLI each give a plain message.

Measured on the builder's PC: about 10 s and about 8,000 tokens of Codex overhead per call. A
tailoring run makes about 3 to 8 calls, because bullets are batched.

## How to use it

```bash
python apps/api/scripts/run_local.py --codex
```

Or type `codex-cli` as the model under Tailor → "Your own model (optional)". In Streamlit,
`codex-cli` can be entered as the model in the sidebar.

## Only on your own computer

The API refuses `codex-cli` for signed-in users, which means any shared deployment. On a server,
it would spend one person's ChatGPT plan on everyone's requests. OpenAI's terms don't allow
sharing an account that way, and the server would need the owner's ChatGPT sign-in.

**Rejected: a proxy that turns the ChatGPT sign-in into an OpenAI-compatible API.** It's
unofficial, can break with any CLI update, and has the same terms problem.

## Limits

- **Usage:** each call uses the weekly Codex allowance, including Codex's own overhead.
- **Speed:** slower than a direct API, because it starts the CLI once per call.
- **Quality:** answers depend on the person's Codex default model (for example GPT-5.6-Luna). The
  same checks as for every model still apply. Nothing unconfirmed reaches a resume.
