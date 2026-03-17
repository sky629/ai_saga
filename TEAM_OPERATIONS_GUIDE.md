# Team Operations Guide

This guide defines how AI Saga development is executed by a multi-role
team and how Codex should orchestrate sub-agents for parallel work.

## 1. Team Roles

- Product Planner (PM)
  - Defines product goals, scope, priorities, and acceptance criteria.
- Tech Lead
  - Owns architecture consistency and cross-domain technical decisions.
- Backend Developer
  - Implements domain/application/infrastructure/presentation logic in backend.
- Frontend Developer
  - Implements UI state, screens, and API integration.
- UI/UX Designer
  - Defines user flows, layouts, interaction patterns, and UX states.
- QA Engineer
  - Owns test strategy, regression coverage, and release quality gates.
- Reviewer
  - Performs code/design review and blocks risky regressions.
- Release Manager
  - Coordinates integration, readiness checks, and release decisions.

## 1.1 Codex Role Mapping

When Codex uses sub-agents, map team roles to agent types as follows:

- Product Planner (PM)
  - `product-manager` or `planner`
- Tech Lead
  - `architect`
- Backend Developer
  - `executor` or `worker`
- Frontend Developer
  - `executor` or `worker`
- UI/UX Designer
  - `designer` or `ux-researcher`
- QA Engineer
  - `test-engineer`, `qa-tester`, or `verifier`
- Reviewer
  - `code-reviewer`, `quality-reviewer`, or `critic`
- Release Manager
  - `planner` or `quality-strategist`

## 1.2 Main Agent Responsibility

- The main agent owns user communication, final decisions, and final
  integration.
- Sub-agents may investigate, implement bounded changes, review, or
  validate, but they do not own final merge decisions.
- If instructions conflict across sub-agents, the main agent resolves
  the conflict and records the decision in the handoff.

## 2. Standard Development Flow

Use this strict sequence for feature development:

1. Planning
2. Design
3. Planning/Design Review and Revision
4. Parallel BE/FE Implementation (TDD-based)
5. QA
6. Release Readiness Check (recommended)
7. Retrospective (recommended)

## 2.1 Sub-Agent Activation Rules

Use sub-agents only when they materially reduce turnaround time or risk.

- Use a single main agent for:
  - Small bug fixes
  - Single-file edits
  - Short explanations
  - Tight, blocking work where delegation would slow execution
- Use sub-agents for:
  - Two or more independent investigations
  - Parallel backend/frontend work after contract freeze
  - Independent implementation across disjoint write scopes
  - Parallel implementation and verification
  - Architecture review or risk review that can run beside coding
- Do not spawn sub-agents just to restate obvious context or duplicate
  work already being done by the main agent.

## 2.2 Parallelization Preconditions

No parallel coding begins unless all items below are true:

- Scope is broken into bounded tasks.
- Each task has a clear owner.
- Each worker has a disjoint write scope.
- API contract is frozen if BE/FE run in parallel.
- The main agent can continue useful work without blocking on all
  sub-agent outputs immediately.

## 3. Stage Gates (Exit Criteria)

No stage may proceed unless all gate items are met.

### 3.1 Planning Gate
- PRD is documented.
- In scope / out of scope are explicit.
- Acceptance criteria are testable.
- Priority and rollout scope are fixed.

### 3.2 Design Gate
- API contract is defined (request/response/error schema).
- Data model impact is documented (DB/migration/caching).
- Sequence diagram or flow spec is documented.
- Edge cases and failure modes are listed.

### 3.3 Review/Revision Gate
- Open decisions count is zero.
- Risks are tracked with owner and mitigation.
- Contract version is frozen for implementation.

### 3.4 Implementation Gate (BE/FE)
- TDD followed (RED -> GREEN -> REFACTOR) for new behavior.
- BE tests pass for impacted modules.
- FE tests pass for impacted modules.
- Lint/format checks pass.
- Contract tests pass (or explicit waiver approved by Tech Lead).
- Parallel work was integrated by the main agent without unresolved file
  ownership conflict.

### 3.5 QA Gate
- P0/P1 bugs are zero.
- Critical user journeys pass in test environment.
- Regression checklist is complete.
- Release note draft is ready.

## 4. TDD Rules (Mandatory)

- No production behavior without a failing test first.
- Unit tests must validate business rules and edge cases.
- Integration tests cover persistence/external adapter behavior.
- E2E tests cover major user flows and error boundaries.
- Bug fixes must include a regression test.

## 4.1 TDD Rules for Sub-Agents

- A worker implementing behavior change must start with a failing test
  for its owned scope.
- A reviewer or verifier agent must call out any production-first change
  that bypassed RED -> GREEN -> REFACTOR.
- If a delegated task cannot safely add tests because the scope is
  unclear, the task returns to the main agent instead of guessing.

## 5. Parallel BE/FE Rules

- API contract freeze is required before parallel coding starts.
- Contract changes during implementation require:
  - Version bump or compatibility strategy
  - Change log entry
  - QA impact review
- Backend and frontend must sync against the same contract version tag.

## 5.1 Write Scope Rules

- Every implementation sub-agent must have explicit file or module
  ownership.
- Two implementation sub-agents must not edit the same file unless the
  main agent explicitly chooses serialized work.
- Shared files such as central config, router registration, dependency
  wiring, or lockfiles should default to main-agent ownership.
- If an unexpected overlap appears, the worker stops and reports the
  conflict instead of overwriting another worker's changes.

## 5.2 Handoff Rules for Parallel Work

Each sub-agent handoff must include:

- Owned scope
- What changed
- Tests run
- Remaining risks
- Open questions
- Files touched

## 6. Quality and Risk Management

### 6.1 Review Priorities
- Behavioral regressions
- Data consistency issues
- Error handling gaps
- Test coverage gaps
- Performance and concurrency risks

## 6.4 Sub-Agent Review Rules

- At least one independent review-oriented agent should be used for
  risky or cross-cutting changes when practical.
- Review agents focus first on regressions, missing tests, contract
  drift, and ownership conflicts.
- Verification should run in parallel with non-overlapping implementation
  when possible.
- The main agent decides whether review findings block integration.

### 6.2 Observability Checklist
- Structured logs for major flows
- Error logs include actionable context
- Critical path metrics/alerts defined
- Rollback path documented

### 6.3 Security Checklist
- AuthN/AuthZ paths validated
- Sensitive data not exposed in logs/responses
- Rate limiting and abuse scenarios considered
- Dependency vulnerabilities reviewed

## 7. Required Artifacts Per Feature

- Planning doc (goal, scope, AC)
- Design doc (contract + data + flow + edge cases)
- Decision log (ADR-style)
- Test plan (unit/integration/e2e)
- QA report (bugs + validation result)
- Release checklist

## 7.1 Required Artifacts Per Delegated Task

- Task statement with owner
- Bounded write scope
- Expected output
- Validation method
- Result summary

## 8. Handoff Template (Use Across Roles)

Use `docs/HANDOFF_TEMPLATE.md` as the default handoff artifact for both
phase-thread and sub-agent workflows, and store filled handoff files in
`docs/handoffs/`.

Each role handoff must include:

- Input
- Output
- Done criteria
- Known risks
- Open questions (must be empty at gate exit)
- Owner

## 8.1 Sub-Agent Task Template

Use `docs/HANDOFF_TEMPLATE.md` with:

- Mode = `sub-agent`
- Handoff Type = `task`
- Scope, validation, and write ownership filled in before delegation

## 8.2 Sub-Agent Return Template

Use `docs/HANDOFF_TEMPLATE.md` with:

- Mode = `sub-agent`
- Status = `done` or `blocked`
- Work summary, validation, and remaining risks filled in by the worker

## 8.3 Phase Thread Handoff Template

Use `docs/HANDOFF_TEMPLATE.md` with:

- Mode = `thread`
- Handoff Type = `phase`, `review`, `qa`, or `integration`
- Input, decisions, and next handoff sections filled before moving to
  the next thread

## 9. Communication Cadence

- Daily sync: status, blockers, contract changes
- Design review checkpoint before implementation
- QA checkpoint before release decision
- Post-release retrospective with action items

## 9.1 Communication Rules for Codex Teams

- The main agent communicates with the user.
- Sub-agents communicate through task results, not directly to the user.
- Status updates should be concise and tied to concrete progress.
- The main agent should not wait on sub-agents reflexively; it should
  continue non-overlapping work while they run.

## 10. Definition of Done (Feature Level)

A feature is done only when:

- Planned acceptance criteria are fully met
- Required tests pass
- QA gate passes (P0/P1 = 0)
- Reviewer and Tech Lead sign-off are complete
- Release Manager confirms readiness

## 11. Codex Multi-Agent Execution Policy

This section defines the default policy Codex should follow.

- Default mode is single-agent execution unless delegation is justified.
- The main agent may spawn sub-agents for independent research,
  implementation, review, or verification.
- The main agent must avoid duplicate delegation on the same unresolved
  task.
- Critical-path work that blocks the very next step should usually stay
  with the main agent.
- Final integration, final user response, and final acceptance judgment
  remain main-agent responsibilities.

## 12. Recommended Delegation Patterns

### 12.1 Research Split

- Main agent continues primary implementation planning.
- `researcher` or `explorer` agents answer bounded codebase questions.

### 12.2 Implementation + Verification

- One worker implements a bounded change.
- One verifier or test-focused agent validates tests, edge cases, and
  regressions in parallel.

### 12.3 Backend/Frontend Split

- Only after API contract freeze.
- Backend and frontend workers use separate write scopes.
- Main agent owns shared contract notes and integration.

### 12.4 Review Split

- A review-oriented agent checks the result after implementation.
- Findings are prioritized by severity and must include concrete file
  references when possible.
