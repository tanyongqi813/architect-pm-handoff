---
name: architect-pm-handoff
description: Codex-only workflow for planning prioritized repository changes, writing difficulty-classified micro-batched Task Specs, and reviewing implementation results. Do not use in implementation agents.
---

# Architect–Executor Handoff

## Host restriction

This skill is exclusively for OpenAI Codex. Implementation agents must not select or execute it; they should use their own project rules or executor skills instead.

If the current host is an implementation agent rather than OpenAI Codex:

- Do not execute this workflow.
- Do not create, advance, or review Task Specs.
- State that this is a Codex-only skill and direct the user to the implementation agent's project rules.
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
4. Assign both a priority and a difficulty level when each Task is first created. These fields are mandatory; never leave either implicit.
5. Create or update `docs/tasks/TASK-xxx.md` using `docs/tasks/TEMPLATE.md` and register it in `docs/TASK_LIST.md`. If the template lacks priority or difficulty fields, add them to the created Task Spec and update the template when it is maintained by this workflow.
6. Mark only tasks with satisfied prerequisites as `READY`; later tasks remain `DRAFT`. Among simultaneously unblocked tasks, recommend the highest-priority task first. Priority never overrides an unsatisfied dependency.
7. Update `docs/ARCHITECTURE.md` only when the effective architecture changes. Create an ADR for consequential or hard-to-reverse decisions.

### Priority and difficulty classification

Every Task Spec and its `docs/TASK_LIST.md` entry must include:

- `优先级`: `P0`, `P1`, `P2`, or `P3`.
  - `P0`: active production outage, exploitable security issue, data-loss risk, or release-blocking emergency. Use rarely.
  - `P1`: current milestone critical path, blocks other accepted tasks, or carries material near-term business or technical risk.
  - `P2`: normal planned work with no immediate blocker. This is the default when no stronger reason exists.
  - `P3`: optional improvement, cleanup, or deferred optimization with low near-term impact.
- `难度等级`: `Low`, `Medium`, or `High`.
  - `Low`: explicit, low-risk work following an established pattern, normally within 1–2 primary files.
  - `Medium`: localized design or diagnosis with moderate interactions, normally within the micro-batch boundary.
  - `High`: cross-module behavior, complex state or data flow, migrations, auth/security, concurrency, performance work, unfamiliar code, or substantial judgment.

Priority expresses urgency and sequencing; difficulty expresses the capability needed to execute the Task. Do not infer one from the other. Do not write product, vendor, model, or agent names such as Cursor or Kimi in the Task Spec's executor recommendation. Consumers may map difficulty levels to their own implementation agents outside the shared project documents.

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

### Approved Task Git sync

Automatic Git sync is opt-in. Read `config.local.toml` in this Skill directory when present; otherwise use the disabled defaults in `config.example.toml`. Never publish `config.local.toml`.

When `git_sync.auto_commit_on_pass = true`, after a `[PASSED]` or `[PASSED_WITH_NOTES]` verdict and all required repository documentation updates:

- Inspect the final diff and status. Commit only the reviewed Task's implementation, tests, generated or migration files required by that Task, its Task Spec, `docs/TASK_LIST.md`, and architecture/ADR updates caused by that Task. Never include unrelated staged or unstaged changes.
- Require all acceptance verification to have passed, no merge/rebase/cherry-pick conflict state, a named branch, no suspected secrets or credentials, and a complete Task record. Stop and report the reason when any condition fails.
- Run `python3 scripts/commit_and_sync_task.py` with an explicit `--path` for every approved file. The script rejects unrelated staged files, sensitive-looking paths, detached HEAD, incomplete Git operations, whitespace errors, and missing upstreams.
- Use commit subject `task(TASK-XXX): <short title>`. The commit body must record Task ID, spec path, review verdict, priority, difficulty, verification commands/results, and every committed path.
- Report the resulting commit SHA, branch, committed paths, and push status in the review response so the approval remains traceable.

When `git_sync.auto_push_on_pass = true`, pass `--push` and synchronize only through the current branch's existing upstream. Never create an upstream implicitly, force-push, amend, rewrite history, switch branches, merge, or open a pull request. If push fails, preserve the local commit, report that it is not synchronized, and do not retry automatically.

Complete this Git sync before selecting or dispatching the next Task. A successful review without a successful configured sync must clearly report the sync blocker, but it does not change the review verdict.

After every review verdict, including repeated review of the same Task, reassess the priority of every non-`PASSED` Task affected by the result. Consider changed dependencies, newly discovered defects or risks, milestone impact, and current business urgency. Update `docs/TASK_LIST.md` and each affected Task Spec when a priority changes, and record `old → new` plus the reason in the review record. If no priority changes, explicitly record that priorities were reassessed and remained unchanged. Select the next `READY` Task only after this reassessment.

Every review response must include a concise `### 优先级复核` section listing each priority change and reason, or stating `已复核，无调整`. This section appears before the executor handoff.

### Executor handoff after review

Treat the heading `### 发给执行代理的下一步指令（难度：Low|Medium|High）` as a strict machine-readable dispatch signal. Output it only when there is exactly one actionable handoff after the verdict, priority reassessment, and repository updates.

An actionable handoff exists only when either:

- `[CHANGES_REQUESTED]` has concrete, recorded correction instructions for the reviewed Task, with a complete Task Spec, known priority and difficulty, and no unresolved product or architecture decision; or
- a next Task is `READY`, all prerequisites are satisfied, its Task Spec is complete, and priority and difficulty are known.

If these conditions are not met, do not output the handoff heading, an empty handoff block, a placeholder, an instruction to wait, or a message addressed to an implementation agent. Report the situation only in the ordinary review/status text for the user. This includes `[BLOCKED]`, a completed stage with no next Task, locked or `DRAFT` Tasks, incomplete planning data, unresolved dependencies, and cases where no single executable Task can be selected. The absence of the heading means `no dispatch` to downstream automation.

- For `[CHANGES_REQUESTED]`, normally return the correction at the same difficulty level. Raise the difficulty when the defect reveals wider impact, architectural uncertainty, security/data risk, or repeated failed correction; update the Task Spec when it changes. Include the Task ID, priority, difficulty, defect summary, required correction, affected files, constraints, and exact verification commands or observable checks. Require a concise Implementation Report and diff summary. Keep the work within the existing task.
- For `[PASSED]` or `[PASSED_WITH_NOTES]`, address the highest-priority unblocked `READY` Task after priority reassessment. Base the instruction on its Task Spec, and include the Task ID, priority, difficulty, spec path, objective, affected files, constraints, and verification. Non-blocking review notes may be mentioned only when relevant to that next task.
- If no actionable handoff exists, state the completion, lock, missing planning information, dependency, or required user decision outside any executor-handoff section. Do not invent a task.

The executor instruction must stand on its own without relying on the surrounding review text. It must direct the executor to implement, test, and report only; it must not ask the executor to select or execute this Codex-only skill, redefine architecture, expand scope, or modify unrelated files.

### Cursor CLI dispatch

Cursor dispatch is optional and CLI-only. Never use GUI automation, computer control, screenshots, window discovery, editor chat navigation, or GUI fallback for this workflow.

- Do not invoke Cursor CLI until the user explicitly authorizes that specific Task dispatch. Enabling this workflow is not standing authorization for future tasks.
- Before dispatch, resolve and verify the repository absolute path, Task ID, Task Spec path, priority, difficulty, and that the user selected Cursor CLI for a `READY` Task or approved correction. The shared Task Spec must remain vendor-neutral. Do not guess a repository from its display name or infer the user's local difficulty-to-agent mapping.
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
- Other implementation-agent handoffs remain manual unless the user separately defines and authorizes a compatible dispatch workflow.
- Do not offer dispatch for `[BLOCKED]` or when no actionable next task exists.

## Response shape

Keep chat output compact:

```markdown
### 架构/技术设计简述
[2–3 sentences]

### Task Spec: TASK-XXX [title]
- 状态与 spec path
- 优先级
- 难度等级
- 涉及文件
- 前置条件
- 核心变更摘要
- 关键约束
- 验证方式
```

The complete specification remains in `docs/tasks/TASK-xxx.md`.

For review responses with exactly one actionable handoff, append:

```markdown
### 发给执行代理的下一步指令（难度：[Low|Medium|High]）
> [A vendor-neutral, self-contained implementation or correction prompt that the user can copy into a suitable executor.]
```

For review responses without an actionable handoff, omit this section entirely.

Only when an actionable handoff exists, the user has mapped it to Cursor, and it has not yet been dispatched, finish with a concise confirmation question such as:

```markdown
是否授权通过 Cursor CLI 在项目 `[absolute path]` 中执行 `TASK-XXX`？
```
