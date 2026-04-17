# r2po-init

CLI tool that bootstraps a new R2PO project repository in the [NovaSoftworks](https://github.com/NovaSoftworks) GitHub organization.

**What it does in one command:**
1. Creates a private GitHub repository in NovaSoftworks
2. Seeds 11 standard R2PO files (issue templates, doc templates, CLAUDE.md, status.md)
3. Makes the first commit and pushes to `main`

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| git | any | `git --version` |
| GitHub CLI | any | `gh --version` |
| r2po-team repo | — | must be at `~/ns/r2po/r2po-team` |

GitHub CLI must be authenticated:
```
gh auth login
```

---

## Installation

```bash
cd ~/ns/r2po/r2po-init
pip install -e . --break-system-packages
```

Then add `~/.local/bin` to your PATH (once, in `~/.bashrc` or `~/.zshrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Reload your shell:
```bash
source ~/.bashrc   # or source ~/.zshrc
```

Verify:
```bash
r2po-init --help
```

---

## Usage

### Argument mode (no prompts)

```bash
r2po-init <repo-name>
```

Example:
```bash
r2po-init my-new-project
```

Output:
```
Initializing NovaSoftworks/my-new-project…

  [✓] Create repository
  [✓] Seed templates
  [✓] Commit and push

Done. https://github.com/NovaSoftworks/my-new-project
```

With a custom description:
```bash
r2po-init my-new-project --description "Handles customer onboarding flow"
```

### Interactive mode

```bash
r2po-init
```

The tool prompts for name and description:
```
Repository name: my-new-project
Description [R2PO project: my-new-project]:
```

---

## Repository naming rules

- Lowercase letters, digits, and hyphens only
- Cannot start or end with a hyphen
- Max 100 characters

Valid: `my-project`, `api-v2`, `r2po-init`  
Invalid: `My-Project`, `my project`, `-bad`, `bad-`

---

## What gets seeded

The following files are copied from `~/ns/r2po/r2po-team` and committed:

```
.github/ISSUE_TEMPLATE/epic.md
.github/ISSUE_TEMPLATE/story.md
.github/ISSUE_TEMPLATE/bug.md
.github/ISSUE_TEMPLATE/task.md
docs/templates/functional-spec.md
docs/templates/architecture-system.md
docs/templates/architecture-platform.md
docs/templates/test-report.md
docs/templates/iteration-plan.md
docs/status.md          ← generated with today's date, Phase 1
CLAUDE.md               ← generated with repo name, description, and GitHub URLs
```

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (including push failure — see warning in output) |
| 1 | Fatal error (repo already exists, auth failed, etc.) |

---

## Known limitations (iteration-1)

- **No R2PO labels**: labels (`epic`, `story`, `bug`, etc.) are not applied automatically yet. Add them manually in GitHub → Settings → Labels.
- **No retry logic**: a transient network error during repo creation will fail immediately.
- **No rollback**: if the tool fails after creating the repo, the orphaned repo must be deleted manually before re-running.
