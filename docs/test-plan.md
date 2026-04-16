# Test Plan

Project: [project name]
Iteration: [iteration name]
Version: 0.1
Status: draft | active | complete
Last updated: [date]
Author: QA (R2PO)

---

## 1. Scope

This test plan covers the stories in [iteration name]:

- [story issue number and title]
- [story issue number and title]

The following are explicitly out of scope for this iteration:
- [item]

---

## 2. Test environment

- System started by: DevOps agent
- Running on: WSL2, Docker Compose
- Branch or commit under test: [branch name or commit hash]
- Date environment was confirmed running: [date]

---

## 3. Test cases

### Story [#issue-number] - [story title]

#### TC-[NNN]: [test case name]

Preconditions:
- [what must be true before this test runs]

Steps:
1. [single action]
2. [single action]
3. [single action]

Expected result: [what should happen]
Actual result: [filled in during execution]
Status: not run / pass / fail

Linked bug: [issue number if failed, otherwise none]

---

## 4. Edge cases and risk areas

List edge cases that cut across stories or that are high risk.

| Area | Risk | Test approach |
|---|---|---|
| [area] | [what could go wrong] | [how it will be tested] |

---

## 5. Execution log

| TC number | Date | Tester | Status | Notes |
|---|---|---|---|---|
| TC-001 | [date] | QA | pass / fail | [notes] |

---

## 6. Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | [date] | Initial draft | QA |
