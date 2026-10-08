---
name: architect-pm-handoff
description: Codex-only workflow for planning repository changes, writing micro-batched Task Specs for an implementation agent, and reviewing its results. Do not use in Cursor.
---

# Architect–Executor Handoff

## Host restriction

This skill is exclusively for OpenAI Codex. Cursor must not select or execute it; Cursor should use its own project or user Rules instead.

If the current host is Cursor:

- Do not execute this workflow.
- Do not create, advance, or review Task Specs.
- State that this is a Codex-only skill and direct the user to the project's Cursor Rules.
- Stop without changing files.

In OpenAI Codex, continue with the workflow below. Codex may select this skill implicitly according to `agents/openai.yaml`, or the user may invoke it explicitly as `$architect-pm-handoff`.

Operate as the architecture and review role when the user requests a feature plan, a Task Spec for Cursor, or review of Cursor's implementation. Do not take over ordinary direct coding requests unless the user asks to use this workflow.

## Establish facts first

Inspect the repository before proposing paths or interfaces. Use these sources when present:

- `AGENTS.md` for shared constraints.
- `docs/ARCHITECTURE.md` for current architecture.
- `docs/TASK_LIST.md` for sequencing and status.
- Relevant implementation and test files for actual behavior.
- `docs/decisions/` for durable decisions.

Do not invent missing facts. Mark material uncertainty as `待确认`; ask the user only when it changes the design materially.

## Planning mode

For a new requirement:

1. Clarify the business outcome, non-goals, affected data flow, compatibility needs, and observable acceptance criteria from available context.
2. Choose the smallest design consistent with the current architecture. Avoid unrelated refactors and new dependencies.
3. Split the work into ordered, independently verifiable tasks. Each task represents one coherent change and normally touches 1–3 primary implementation files. Required tests, types, migrations, generated files, and workflow metadata may be additional.
4. Create or update `docs/tasks/TASK-xxx.md` using `docs/tasks/TEMPLATE.md` and register it in `docs/TASK_LIST.md`.
5. Mark only tasks with satisfied prerequisites as `READY`; later tasks remain `DRAFT`.
6. Update `docs/ARCHITECTURE.md` only when the effective architecture changes. Create an ADR for consequential or hard-to-reverse decisions.

Present a concise design summary and identify the next `READY` task. The repository files, not the chat response, are the source of truth.

## Review mode

Trigger review when the user supplies a diff, error, test result, or Implementation Report and asks for review.

Check:

- Alignment with the Task Spec, architecture, and constraints.
- Correctness at boundaries, error handling, types, state transitions, security, resource lifecycle, and compatibility.
- Scope discipline and whether verification proves the acceptance criteria.

Return exactly one verdict:

- `[PASSED]`: acceptance criteria and verification are satisfied.
- `[PASSED_WITH_NOTES]`: safe to accept; notes are non-blocking.
- `[CHANGES_REQUESTED]`: concrete defects require correction.
- `[BLOCKED]`: a product or architecture decision is required.

For `[CHANGES_REQUESTED]`, update the same Task Spec with focused refactor instructions and set its status accordingly. Do not create a new feature task or propose broad redesign unless the defect proves the approved design invalid.

For `[PASSED]` or `[PASSED_WITH_NOTES]`, set the reviewed task to `PASSED`, record material notes, and promote the next unblocked task from `DRAFT` to `READY`. Do not implement it.

## Response shape

Keep chat output compact:

```markdown
### 架构/技术设计简述
[2–3 sentences]

### Task Spec: TASK-XXX [title]
- 状态与 spec path
- 涉及文件
- 前置条件
- 核心变更摘要
- 关键约束
- 验证方式
```

The complete specification remains in `docs/tasks/TASK-xxx.md`.
