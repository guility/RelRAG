---
name: intermediate-git-commit
description: Creates an intermediate git commit after a unitary task is completed. Use when a single discrete task has been finished and a savepoint commit is needed, or when the user asks for an intermediate/checkpoint commit.
---

# Intermediate Git Commit

## When to Use

Apply this skill **every time a unitary task is completed**:
- One feature, fix, or refactor is done and working
- A logical chunk of work is finished (e.g. "add endpoint", "fix validation", "extract helper")
- Before starting the next unrelated change

Do **not** commit when:
- There are no staged or unstaged changes
- The user explicitly asked not to commit
- The task is only partially done or broken

## Instructions

1. **Check state**
   - Run `git status`. If nothing to commit (working tree clean), skip the commit and say so.
   - Ensure you're in a git repo; if not, skip.

2. **Stage only task-relevant changes**
   - Stage files that belong to the completed task: `git add <paths>` or `git add -p` for partial staging.
   - Do not stage unrelated or debug-only changes (e.g. commented code, logs, unrelated files).

3. **Write the commit message**
   - One short line (≤72 chars), imperative mood.
   - Describe what was done in this unit of work, not the whole branch.
   - Prefer: `Add X`, `Fix Y`, `Refactor Z` — not "Added X" or "Fixes Y".

4. **Create the commit**
   - Run: `git commit -m "<message>"`.
   - If commit fails (e.g. pre-commit hook), report the error and do not retry without user input.

5. **Confirm**
   - Briefly confirm: e.g. "Committed as: &lt;message&gt;".

## Message Examples

| Task completed        | Good message                    | Avoid                    |
|-----------------------|----------------------------------|--------------------------|
| Add login endpoint    | `Add POST /login endpoint`      | "Added some API stuff"   |
| Fix date validation   | `Fix date validation in form`   | "fixes"                  |
| Extract auth helper   | `Extract auth helper to utils`  | "refactor"               |
| Update dependency     | `Update requests to 2.31`       | "Update deps" (too vague)|

## Summary Checklist

Before committing:
- [ ] There are changes to commit
- [ ] Only files for the completed task are staged
- [ ] Message is imperative, short, and describes this unit of work
- [ ] No unrelated or temporary changes included
