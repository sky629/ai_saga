# Git Worktree Guide

This guide standardizes feature development using `git worktree`.
Use it together with `TEAM_OPERATIONS_GUIDE.md` when work is delegated,
parallelized, or split across isolated ownership boundaries.

## 1. Why Worktree

Use worktrees to run multiple branches in parallel without repeated checkout:

- Safer parallel development (BE/FE/QA in isolated directories)
- Fewer branch-switch conflicts
- Faster context switching
- Clear branch-to-folder ownership

## 2. Core Rules

1. Never implement features directly on `main`.
2. One worktree = one branch.
3. One active owner per worktree.
4. Use naming conventions for both branch and folder.
5. Remove worktree after merge.

## 2.1 When Worktree Is Required

Worktree usage is mandatory for:

- Parallel implementation by multiple people or agents
- Backend/frontend parallel work after contract freeze
- Long-running feature branches
- High-conflict or high-churn work touching shared areas
- Risky refactors, migrations, or release/hotfix work that must stay
  isolated

## 2.2 When Worktree Is Recommended

- Multi-step feature work that will take more than one session
- QA validation on a branch separate from active implementation
- Review or repro work that benefits from a clean isolated tree

## 2.3 When Worktree May Be Skipped

- Small single-agent bug fixes
- Single-file or low-risk document changes
- Short-lived local tasks with no ownership conflict

If worktree is skipped, the branch must still not be `main`, and the
task must not conflict with active delegated work.

## 3. Naming Conventions

### Branch
- `feat/<topic>`
- `fix/<topic>`
- `chore/<topic>`

Examples:
- `feat/dice-system`
- `fix/session-cache-loop`
- `chore/test-stability`

### Worktree Folder
- `../ai_saga-wt/wt-<short-topic>`

Examples:
- `../ai_saga-wt/wt-dice-system`
- `../ai_saga-wt/wt-session-cache`

## 4. Standard Commands

## 4.1 Create a New Worktree from main

```bash
git fetch origin
git worktree add ../ai_saga-wt/wt-dice-system -b feat/dice-system origin/main
```

## 4.2 List Worktrees

```bash
git worktree list
```

## 4.3 Remove Worktree (after merge)

```bash
git worktree remove ../ai_saga-wt/wt-dice-system
git branch -d feat/dice-system
```

If branch is already removed remotely and local metadata is stale:

```bash
git worktree prune
```

## 5. Recommended Team Mapping

- Backend Developer: one BE worktree per backend feature branch
- Frontend Developer: one FE worktree per frontend feature branch
- QA Engineer: dedicated QA verification worktree
- Reviewer: optional review worktree for final verification

## 6. Parallel Development Workflow

1. Freeze contract version (API/schema/error format)
2. Create BE and FE worktrees from the agreed base
3. Implement in parallel under separate branches
4. Run tests/lint inside each worktree
5. Rebase branch on latest `origin/main`
6. Open PRs
7. Merge in agreed order:
   - contract or schema foundation
   - backend
   - frontend
   - QA/fixes

## 6.1 Codex Use in Worktrees

- The main agent decides whether a task needs isolated worktrees.
- If sub-agents or parallel workers are used, assign one worktree per
  implementation owner when feasible.
- Shared integration files should remain under main-agent control unless
  explicitly assigned.
- If a worktree path is outside the default writable workspace, ensure
  the execution environment allows writing there before delegating.

## 7. Merge/Rebase Policy

- Rebase before opening final PR:

```bash
git fetch origin
git rebase origin/main
```

- Resolve conflicts in the feature worktree only.
- Never force-push shared review branches unless explicitly agreed.

## 8. Validation Checklist Per Worktree

Before PR:

- Branch is correct (not `main`)
- `git status` clean or expected changes only
- Tests for changed scope pass
- Lint/format pass
- No unrelated file changes

Suggested commands:

```bash
uv run pytest
uv run black app/ tests/
uv run isort app/ tests/
uv run flake8 app/ tests/
```

## 9. Conflict Prevention Tips

- Keep PR scope small and focused.
- Avoid touching shared contract files without coordination.
- Announce schema/contract updates immediately.
- Use explicit ownership for high-churn files.

## 10. Recovery Playbook

### Case A: Worktree folder deleted manually

```bash
git worktree prune
```

### Case B: Branch exists but worktree path broken

```bash
git worktree list
git worktree remove <broken-path>
git worktree add <new-path> <branch>
```

### Case C: Need to hotfix while feature work continues

Create a separate hotfix worktree:

```bash
git worktree add ../ai_saga-wt/wt-hotfix-auth -b fix/auth-token origin/main
```

## 11. Team Policy Summary

- Mandatory for parallel, isolated, long-running, or high-risk work:
  use worktrees
- Mandatory: branch/worktree naming convention
- Mandatory: cleanup after merge
- Recommended: one role, one active worktree at a time
- Allowed: small single-agent work may stay outside a dedicated worktree
  if conflict risk is low
