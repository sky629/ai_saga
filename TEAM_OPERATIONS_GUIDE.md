# Team Operations Guide

This guide defines how AI Saga development is executed by a multi-role team.

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

## 2. Standard Development Flow

Use this strict sequence for feature development:

1. Planning
2. Design
3. Planning/Design Review and Revision
4. Parallel BE/FE Implementation (TDD-based)
5. QA
6. Release Readiness Check (recommended)
7. Retrospective (recommended)

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

## 5. Parallel BE/FE Rules

- API contract freeze is required before parallel coding starts.
- Contract changes during implementation require:
  - Version bump or compatibility strategy
  - Change log entry
  - QA impact review
- Backend and frontend must sync against the same contract version tag.

## 6. Quality and Risk Management

### 6.1 Review Priorities
- Behavioral regressions
- Data consistency issues
- Error handling gaps
- Test coverage gaps
- Performance and concurrency risks

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

## 8. Handoff Template (Use Across Roles)

Each role handoff must include:

- Input
- Output
- Done criteria
- Known risks
- Open questions (must be empty at gate exit)
- Owner

## 9. Communication Cadence

- Daily sync: status, blockers, contract changes
- Design review checkpoint before implementation
- QA checkpoint before release decision
- Post-release retrospective with action items

## 10. Definition of Done (Feature Level)

A feature is done only when:

- Planned acceptance criteria are fully met
- Required tests pass
- QA gate passes (P0/P1 = 0)
- Reviewer and Tech Lead sign-off are complete
- Release Manager confirms readiness
