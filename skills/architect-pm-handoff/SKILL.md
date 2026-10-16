---
name: architect-pm-handoff
description: Codex-only workflow for planning repository changes, assigning micro-batched Task Specs to Cursor or Kimi, and reviewing implementation results. Do not use in implementation agents.
---

# Architect–Executor Handoff

## Host restriction

This skill is exclusively for OpenAI Codex. Cursor and Kimi must not select or execute it; implementation agents should use their own project rules or executor skills instead.

If the current host is Cursor, Kimi, or another implementation agent:

- Do not execute this workflow.
- Do not create, advance, or review Task Specs.
- State that this is a Codex-only skill and direct the user to the project's Cursor Rules.
- Stop without changing files.

In OpenAI Codex, continue with the workflow below. Codex may select this skill implicitly according to `agents/openai.yaml`, or the user may invoke it explicitly as `$architect-pm-handoff`.

Operate as the architecture and review role when the user requests a feature plan, a Task Spec for an implementation agent, or review of implementation results. Do not take over ordinary direct coding requests unless the user asks to use this workflow.

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
4. Assign a recommended executor in the Task Spec. Use Kimi for low-risk, explicit work that follows an established pattern and is normally limited to 1–2 primary files. Use Cursor for cross-module work, complex state or data flow, migrations, auth/security, concurrency, performance work, unfamiliar code, or tasks requiring substantial diagnosis or judgment. If executor suitability is uncertain, choose Cursor.
5. Create or update `docs/tasks/TASK-xxx.md` using `docs/tasks/TEMPLATE.md` and register it in `docs/TASK_LIST.md`.
6. Mark only tasks with satisfied prerequisites as `READY`; later tasks remain `DRAFT`.
7. Update `docs/ARCHITECTURE.md` only when the effective architecture changes. Create an ADR for consequential or hard-to-reverse decisions.

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

### Executor handoff after review

After the verdict and repository records are updated, end every review response with a directly copyable section titled `### 发给 Cursor 的下一步指令` or `### 发给 Kimi 的下一步指令`, matching the Task Spec's recommended executor.

- For `[CHANGES_REQUESTED]`, normally return the correction to the same executor. Escalate from Kimi to Cursor when the defect reveals cross-module impact, architectural uncertainty, security/data risk, or repeated failed correction. Include the Task ID, defect summary, required correction, affected files, constraints, and exact verification commands or observable checks. Require a concise Implementation Report and diff summary. Keep the work within the existing task.
- For `[PASSED]` or `[PASSED_WITH_NOTES]`, address the next `READY` task to its recommended executor. Base the instruction on its Task Spec, and include the Task ID, spec path, objective, affected files, constraints, and verification. Non-blocking review notes may be mentioned only when relevant to that next task.
- If no unblocked next task exists, state that the current planned stage is complete and do not invent a task. If planning is incomplete, direct the user back to Codex for planning rather than asking an implementation agent to design the next phase.
- For `[BLOCKED]`, do not issue an implementation prompt. In the same section, state the decision needed from the user and that the implementation agent should wait.

The executor instruction must stand on its own without relying on the surrounding review text. It must direct the executor to implement, test, and report only; it must not ask the executor to select or execute this Codex-only skill, redefine architecture, expand scope, or modify unrelated files.

### Cursor CLI dispatch

Cursor dispatch is optional and CLI-only. Never use GUI automation, computer control, screenshots, window discovery, editor chat navigation, or GUI fallback for this workflow.

- Do not invoke Cursor CLI until the user explicitly authorizes that specific Task dispatch. Enabling this workflow is not standing authorization for future tasks.
- Before dispatch, resolve and verify the repository absolute path, Task ID, Task Spec path, and that the task is assigned to Cursor and marked `READY` or requires an approved correction. Do not guess a repository from its display name.
- Confirm `agent` or `cursor-agent` is installed and authenticated. If the CLI is unavailable or authentication fails, preserve the copyable handoff and report the blocker; do not fall back to the Cursor GUI.
- Run Cursor CLI with the repository root as its working directory. Start a fresh non-interactive session for each Task; do not use `--resume` or `--continue` unless the user explicitly requests preserved Cursor context.
- Send only a compact Task-Spec pointer when the repository contains the complete current instructions: `执行 @docs/tasks/TASK-XXX.md；严格遵守 AGENTS.md 与任务约束，只完成该任务；完成验证后输出 Implementation Report 和 diff 摘要。`
- Use print mode with text or structured output. Permit file modification only for an authorized implementation Task; use the installed CLI's supported non-interactive write flag when required. Do not enable broader permissions than the Task needs.
- Prefer `python3 scripts/dispatch_cursor_cli.py --repo <absolute-path> --task docs/tasks/TASK-XXX.md` for authorized dispatch, resolving the script path relative to this Skill directory. Its default idle threshold is 12 minutes without a `stream-json` event. Add `--allow-recovery` only when the user has authorized automatic recovery for that dispatch.
- On the first confirmed stall, the dispatcher terminates the current CLI process before recovery, records output in a temporary log, invokes the macOS `Developer: Restart Extension Host` command through `scripts/restart_cursor_extension_host.sh`, and runs one read-only health probe.
- If the stalled attempt changed the working tree, recover the Extension Host but do not retry; preserve the partial changes for Codex review. If the working tree state is unchanged and the health probe passes, retry once in a fresh CLI session. If that retry stalls or fails, stop and report `[BLOCKED]`; never restart or retry in a loop.
- Automatic recovery requires macOS, a running Cursor application, Accessibility permission for the calling terminal/Codex process, and explicit authorization for the current dispatch. If any prerequisite is missing, stop without GUI fallback or process-killing workarounds.
- Do not start parallel Cursor agents, poll another session, or send follow-ups automatically. A CLI process may finish and its final output may be captured, but further execution requires a new user request or review decision.
- After the CLI exits, report the command outcome and retain its Implementation Report for Codex review. A zero exit status or completion message is not a review verdict.
- Kimi handoffs remain manual unless the user separately defines and authorizes a Kimi CLI workflow.
- Do not offer dispatch for `[BLOCKED]` or when no actionable next task exists.

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

For review responses, append:

```markdown
### 发给 [Cursor 或 Kimi] 的下一步指令
> [A self-contained implementation or correction prompt that the user can copy directly into the assigned executor.]
```

When a Cursor prompt is actionable and has not yet been dispatched, finish with a concise confirmation question such as:

```markdown
是否授权通过 Cursor CLI 在项目 `[absolute path]` 中执行 `TASK-XXX`？
```
