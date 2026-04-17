# Functional Specification

Project: r2po-init
Version: 0.1
Status: draft
Last updated: 2026-04-17
Author: Product Owner (R2PO)

---

## 1. Purpose

`r2po-init` is a command-line tool that automates the initialization of a new R2PO project repository in the NovaSoftworks GitHub organization. It is for developers on the R2PO team who need to start a new project without manually performing a repeatable, error-prone sequence of GitHub setup steps. Without this tool, a developer must create the repo, add six labels, copy four issue templates, copy five doc templates, write a status file and CLAUDE.md, make a first commit, and push — all by hand, every time.

---

## 2. Users and roles

| Role | Description |
|---|---|
| Developer | The R2PO team member who runs the tool from a WSL2 terminal to initialize a new project repo. This is the only user type. |

---

## 3. System overview

The developer invokes the tool with a repo name, either as a CLI argument or in response to an interactive prompt. The tool then performs the full initialization sequence: creates a private GitHub repository in the NovaSoftworks organization, applies the six standard R2PO labels, seeds the repository with issue templates and documentation templates, creates the initial status file and CLAUDE.md, makes a single first commit, and pushes to the remote.

If a step fails due to a network error, the tool retries it up to three times. If the failure is unrecoverable, the tool rolls back every GitHub-side change it made during that run, writes a structured error report to disk, and exits with a non-zero code.

The developer is left with a repo that is immediately ready for Phase 1 of the R2PO workflow.

---

## 4. User flows

### 4.1 CLI invocation (argument mode)

Actor: Developer
Goal: Initialize a new R2PO project repo without any prompts.

Steps:
1. Developer runs `r2po-init <repo-name>` with an optional `--description` flag.
2. Tool validates the repo name (see BR-001, BR-002).
3. Tool creates a private GitHub repo named `<repo-name>` in NovaSoftworks with the provided or auto-generated description (see BR-003).
4. Tool creates or overrides the six standard R2PO labels on the new repo (see BR-004).
5. Tool copies the four issue templates from the hardcoded r2po-team source path into `.github/ISSUE_TEMPLATE/` in the new repo.
6. Tool copies the five doc templates from the hardcoded r2po-team source path into `docs/` in the new repo.
7. Tool creates `docs/status.md` with phase set to `1 - Discovery`.
8. Tool creates `CLAUDE.md` at the repo root with a project stub.
9. Tool makes a single commit containing all files seeded in steps 5–8.
10. Tool pushes the commit to the remote. If push fails, it reports the error without rolling back (see BR-009).
11. Tool prints a success summary listing all completed steps and the repo URL.

Alternative paths:
- Repo already exists: tool aborts at step 3 with a clear error message and no changes made (see BR-001).
- Network error at any step: tool retries up to 3 times before treating the step as a hard failure (see BR-005).
- Hard failure after GitHub-side changes were made: tool rolls back (see BR-006) and writes an error report (see BR-007).
- Hard failure before any GitHub-side changes: tool writes an error report and exits without rollback.

### 4.2 Interactive invocation

Actor: Developer
Goal: Initialize a new R2PO project repo when the repo name is not known at invocation time.

Steps:
1. Developer runs `r2po-init` with no arguments.
2. Tool prompts: `Repository name:`. Developer enters the name.
3. Tool prompts: `Description [R2PO project: <name>]:`. Developer accepts the default by pressing Enter or types a custom description.
4. Flow continues from step 2 of flow 4.1.

Alternative paths:
- Developer provides the repo name as a CLI argument but omits `--description`: tool skips the name prompt and prompts only for description.

### 4.3 Error recovery (rollback)

Actor: Tool (automatic, no developer input required)
Goal: Leave no orphaned state on GitHub after a failed run.

Steps:
1. Hard failure is detected (retries exhausted or non-retryable error received).
2. Tool logs the failure and begins rollback in reverse order of the steps completed.
3. For each GitHub-side change made during this run (in reverse): tool attempts to undo it (delete created labels, delete created repo).
4. If a rollback step itself fails, the tool records it in the error report and continues rolling back remaining steps.
5. Tool writes a structured error report to disk (see BR-008).
6. Tool prints the path to the error report and exits with a non-zero code.

---

## 5. Business rules

- **BR-001**: If a repository with the given name already exists in the NovaSoftworks organization, the tool aborts immediately. No GitHub-side changes are made. This condition is non-retryable.
- **BR-002**: All repositories created by this tool are private. There is no option to create a public repository.
- **BR-003**: If the developer provides no description (CLI flag absent and interactive prompt accepted with default), the tool sets the description to `R2PO project: <repo-name>`.
- **BR-004**: The six standard R2PO labels are `epic`, `story`, `spike`, `bug`, `blocked`, and `needs-review`. If a label with one of these names already exists on the repo, its color and description are overwritten to match the R2PO standard. Labels not in this set are not modified.
- **BR-005**: Any step that makes a GitHub API call is retried up to 3 times on network errors (connection timeout, transient 5xx response). The delay between retries is at the Architect's discretion. After 3 failed attempts, the step is treated as a hard failure.
- **BR-006**: On hard failure, the tool rolls back all GitHub-side changes made during the current run, in reverse order. "GitHub-side changes" means: repo creation and label creation. Local filesystem writes (template files staged for commit) are not rolled back.
- **BR-007**: On any abort (hard failure or non-retryable error that occurs after at least one GitHub-side change has been made), the tool writes a structured error report. The report includes: the step that failed, the error message, and the outcome (success or failure) of each rollback action taken.
- **BR-008**: The first commit contains exactly the following files: `.github/ISSUE_TEMPLATE/epic.md`, `.github/ISSUE_TEMPLATE/story.md`, `.github/ISSUE_TEMPLATE/spike.md`, `.github/ISSUE_TEMPLATE/bug.md`, `docs/functional-spec.md`, `docs/architecture/system.md`, `docs/architecture/platform.md`, `docs/test-plan.md`, `docs/test-report.md`, `docs/status.md`, and `CLAUDE.md`. No other files are included in this commit.
- **BR-009**: The tool attempts to push the first commit to the remote after it is created. If the push fails, the tool reports the error clearly in its output but does not treat it as a hard failure and does not trigger rollback. The developer is responsible for pushing manually in that case.
- **BR-010**: The source paths for issue templates and doc templates are hardcoded to the r2po-team repository location on the local filesystem. The tool does not fetch templates from the network.
- **BR-011**: Rollback deletes only resources created during the current run. Pre-existing resources on GitHub are never modified or deleted by a rollback.
- **BR-012**: A non-retryable error is one that indicates a state the developer must resolve before retrying: repository already exists, authentication failure, insufficient permissions. These errors trigger an immediate abort and error report, with rollback of any GitHub-side changes already made.

---

## 6. Non-functional requirements

### 6.1 Performance

Under normal network conditions, the full initialization sequence must complete in under 2 minutes. Each individual GitHub API call must receive a response within 30 seconds before the tool considers it a timeout.

### 6.2 Security

The tool relies entirely on the developer's existing `gh` CLI authentication. It does not handle, store, or transmit credentials. No secrets are written to disk by the tool. The error report written on failure must not include authentication tokens or other sensitive values from API responses.

### 6.3 Reliability

After any failed run, the GitHub state must be as if the tool was never run: no orphaned repository, no orphaned labels. This is guaranteed by the rollback mechanism (BR-006). A failed run must never prevent a subsequent run with the same repo name from succeeding, subject to the developer resolving the underlying error.

### 6.4 Constraints

- The tool runs on WSL2. It must not depend on features unavailable in a WSL2 Linux environment.
- `gh` CLI and `git` must be installed and authenticated on the developer's machine. The tool does not install or configure these.
- The NovaSoftworks organization name is hardcoded. The tool does not support other GitHub organizations.
- The r2po-team source directory must be present on the local filesystem at a hardcoded path. The tool does not clone or fetch r2po-team.

---

## 7. Out of scope

- Linking the new repository to the R2PO Board GitHub Project
- Non-interactive or CI mode (e.g. a `--no-input` flag)
- Configuration file or environment variable overrides for org name, source paths, or label definitions
- Partial resume after a failed run (the tool is one-shot; re-run after fixing the underlying error)
- Post-initialization steps such as triggering a Phase 1 agent or creating any GitHub issues
- Repository visibility options other than private
- Any modification of an existing repository

---

## 8. Open questions

| # | Question | Raised by | Status |
|---|---|---|---|
| 1 | What is the exact hardcoded path to the r2po-team source directory? | PO | Open — to be resolved by Architect in system.md |
| 2 | What is the file path and format of the error report written on abort? | PO | Open — to be resolved by Architect in system.md |
| 3 | What are the standard color codes and descriptions for the six R2PO labels? | PO | Open — to be resolved by Architect in system.md |
| 4 | What is the content of the CLAUDE.md stub created for the new project? | PO | Open — to be resolved by Architect in system.md |

---

## 9. Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 2026-04-17 | Initial draft | PO |
