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

---

# Iteration-2 Test Report

Project: r2po-init
Iteration: iteration-2
Date range: 2026-04-17 to 2026-04-17
Author: QA (R2PO)

---

## Summary

| Metric | Count |
|---|---|
| Stories in scope | 6 |
| Test cases written | 49 (108 total cumulative) |
| Passed | 49 |
| Failed | 0 |
| Skipped | 0 |
| Bugs filed | 0 |

**Overall assessment: shippable.** All six iteration-2 stories are implemented and tested. The tool now applies R2PO labels, retries transient API errors, rolls back on failure, writes an error report on abort, and supports interactive prompt mode with full progress output.

---

## Story results

### #5 — Apply R2PO labels (6 tests)

All acceptance criteria met:
- `apply_labels` creates all 6 R2PO labels when none exist.
- `apply_labels` updates color and description when a label already exists (override, not skip).
- Mixed case (some existing, some new) handled correctly.
- Wired into initializer between Create repository and Seed templates.
- Labels applied via `_retryable_api_call` — transient failures are retried.

### #11 — Retry on network errors (14 tests)

All acceptance criteria met:
- `_retryable_api_call` retries on 5xx GitHub errors.
- `_retryable_api_call` retries on `ConnectionError` and `OSError`.
- Does NOT retry on 4xx (401, 403, 404, 422) — these are non-retryable.
- Sleeps `GITHUB_API_RETRY_DELAY_SECONDS` between attempts.
- Does not sleep after the final failed attempt.
- Raises last error after `GITHUB_API_RETRY_COUNT` exhausted.
- `create_repo` retries the raw API call; exception classification happens after retry gives up.
- `apply_labels` wraps all label API calls with retry.

### #12 — Rollback on failure (7 tests)

All acceptance criteria met:
- On unexpected failure after repo creation, `delete_repo` is called.
- `RepoExistsError` does NOT trigger rollback (no repo was created).
- On seed failure, rollback still deletes the repo.
- `on_step("Rollback", True)` fired for visibility.
- Rollback uses a journal (`list[_RollbackAction]`) iterated in reverse.
- Best-effort: rollback failure is silenced, not re-raised.

### #13 — Error report on abort (10 tests)

All acceptance criteria met:
- `write(report)` creates a `.txt` file in dest_dir (defaults to cwd).
- Filename format: `r2po-init-error-<YYYY-MM-DDTHH-MM-SS>.txt`.
- Report contains repo name, error message, steps completed, rollback actions.
- Steps and rollback sections omitted when empty.
- Error report path included in `Result.error_report_path`.
- CLI prints error report path when failure includes one.

### #9 — Interactive prompt mode (5 tests)

All acceptance criteria met:
- Running `r2po-init` without arguments prompts for name.
- Invalid name re-prompts until a valid one is entered.
- Description prompted with default `R2PO project: <name>`.
- Pressing Enter accepts the default description.
- In argument mode, description is never prompted.

### #10 — Progress output and exit codes (8 tests)

All acceptance criteria met:
- Header "Initializing NovaSoftworks/<name>…" printed before steps.
- Each step printed as it completes via `on_step` callback.
- "Done. <url>" on success.
- "Failed: <message>" on fatal failure.
- Push failure warning printed; exit code remains 0.
- Error report path printed when present.
- Exit code 0 on success and non-fatal push failure.
- Exit code 1 on fatal failure.

### README (not a story — user-requested)

`README.md` written covering: prerequisites, installation, usage (argument and interactive mode), repo naming rules, seeded files list, exit codes, and known limitations.

---

## Risks for iteration-3

- **No dry-run mode**: `r2po-init --dry-run` to preview what would happen without touching GitHub.
- **No undo command**: `r2po-init --delete <name>` to tear down a repo initialized by mistake.
- **PATH not set automatically**: `~/.local/bin` must be on PATH; setup could be automated by a post-install script.

---

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 2026-04-17 | Iteration-1 report | QA |
| 0.2 | 2026-04-17 | Iteration-2 report appended | QA |
