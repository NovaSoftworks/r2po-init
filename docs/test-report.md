# Test Report

Project: r2po-init
Iteration: iteration-1
Date range: 2026-04-17 to 2026-04-17
Author: QA (R2PO)

---

## Summary

| Metric | Count |
|---|---|
| Stories in scope | 4 |
| Test cases written | 59 |
| Passed | 59 |
| Failed | 0 |
| Skipped | 0 |
| Bugs filed | 0 |

**Overall assessment: shippable.** The four stories deliver a working end-to-end happy path. `r2po-init <name>` creates a private repo, seeds 11 files, and makes the first commit and push.

---

## Story results

### #8 — Initialize a repo via CLI arguments (21 tests)

All acceptance criteria met:
- `r2po-init my-project` completes without prompts; description auto-generates as `R2PO project: my-project`.
- `--description` flag accepted and passed through.
- Invalid names (uppercase, spaces, leading/trailing hyphens, single hyphen) rejected before any GitHub calls.
- `--help` prints usage.
- Exit code 0 on success, 1 on failure.
- Push failure returns exit 0 with a warning (per BR-009).

One defect caught and fixed during development: the description prompt was appearing in argument mode (when only name was supplied). Fixed before merge — description prompts only appear in interactive mode (story #9, not yet implemented).

### #4 — Create private GitHub repository (15 tests)

All acceptance criteria met:
- Private repo created in NovaSoftworks.
- `RepoExistsError` raised (non-retryable) on 422 name-taken responses; inspects `errors[0].field` — not top-level message, which is API-unstable.
- `AuthError` raised on 401/403.
- `delete_repo` is safe to call when repo does not exist (used in rollback).

### #6 — Seed issue templates and doc templates (12 tests)

All acceptance criteria met:
- `validate_source` runs before any GitHub call; error names the expected path.
- `seed` produces exactly 11 files at the correct relative paths.
- `docs/status.md` contains `Phase: 1 - Discovery` and today's date.
- `CLAUDE.md` contains repo name, description, and both GitHub URLs.

### #7 — Make first commit and push to remote (11 tests)

All acceptance criteria met:
- Commit on `main` branch (not `master`) using provided message.
- Credential store file used for push auth — token never in process args.
- Credential file deleted after push on both success and failure.
- Push failure non-fatal: `PushResult(committed=True, pushed=False)` returned; no exception raised.

Two test-infrastructure defects found and fixed:
1. Patching `subprocess.run` globally intercepted real git calls — fixed by saving original function before patch.
2. Invalid repo name test initially used `real_subprocess` (undefined alias) — fixed by using `_real_subprocess_run`.

---

## Risks for iteration-2

- **No retry logic (#11)**: a transient network error during `create_repo` or `create_labels` will fail immediately with no retry. Low risk for manual use; medium risk in poor network conditions.
- **No rollback (#12)**: a failure mid-run (e.g. after repo creation) leaves an orphaned repo. Developer must delete it manually before re-running.
- **No labels (#5)**: the initialized repo has no R2PO labels. Team cannot use `epic`, `story`, etc. until labels are added manually or story #5 is implemented.
- **`~/.local/bin` not on PATH**: `r2po-init` command not available without PATH configuration. Needs documentation.

---

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 2026-04-17 | Iteration-1 report | QA |
