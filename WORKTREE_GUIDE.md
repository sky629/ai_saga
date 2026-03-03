# Git Worktree Guide

This guide standardizes feature development using `git worktree`.

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

- Mandatory: all feature work through worktrees
- Mandatory: branch/worktree naming convention
- Mandatory: cleanup after merge
- Recommended: one role, one active worktree at a time
