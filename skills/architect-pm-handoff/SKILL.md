---
name: architect-pm-handoff
description: Lead-AI workflow for prioritized repository planning, context-efficient handoffs to downstream agents, and implementation review. Produces durable Task Specs, short per-attempt Execution Capsules, and separate Review Records; use only when acting as the responsible planner/reviewer.
---

# Lead AI–Executor Handoff

## Boundary

This skill is for the **lead AI** responsible for architecture, planning, sequencing, review, and acceptance. The lead may be Claude, Codex, or another agent with that assigned authority. A downstream agent whose assignment is implementation-only must not run the planning/review workflow or advance Task state.

Role assignment, not vendor identity, controls behavior. The same AI may use this skill only while explicitly acting as lead; an executor must follow the current Execution Capsule and return evidence without redefining architecture or scope. Keep shared Task Specs, Execution Capsules, and Review Records vendor-neutral; channel- or model-specific behavior belongs in an adapter.

The lead AI must not take over implementation unless the user separately requests direct coding. Repository files are the source of truth, but a downstream agent receives only the bounded projection needed for its current attempt.

## Establish facts

Inspect the repository before proposing paths or interfaces. Prefer, when present:

- `AGENTS.md` for shared repository constraints.
- `docs/ARCHITECTURE.md` and `docs/decisions/` for system boundaries and durable decisions.
- `docs/TASK_LIST.md` for sequencing and status.
- The current Task Spec and relevant implementation/tests for actual behavior.

Do not invent missing paths, interfaces, file allowlists, commands, or baseline failures. Mark material uncertainty as `待确认`; ask only when it changes the design materially. When repository behavior conflicts with documentation, record the conflict and request an architecture decision.

## Three-layer record model

Keep these responsibilities separate:

1. **Task Spec — durable planning facts.** Store business outcome and non-goals, architecture and compatibility requirements, acceptance criteria, dependencies, priority, difficulty, primary interfaces, and long-lived constraints. Do not append execution transcripts or accumulated review history. Read [references/task-spec.md](references/task-spec.md) when creating or migrating a Task Spec.
2. **Execution Capsule — one-attempt execution contract.** Create a short, self-contained, immutable-per-attempt projection under `docs/execution/TASK-XXX/attempt-NN.md` (or the repository's established equivalent). Read [references/executor-handoff.md](references/executor-handoff.md) whenever creating or revising a capsule.
3. **Review Record — append-only review evidence.** Store each verdict and findings separately under `docs/reviews/TASK-XXX/attempt-NN.md` (or the repository's established equivalent). Read [references/review-record.md](references/review-record.md) whenever recording a review.

Use matching attempt numbers across capsule and review record. A correction creates a new capsule/review attempt; never overwrite the historical contract. Task status and current attempt pointers may remain in `docs/TASK_LIST.md` or compact Task Spec metadata.

## Planning mode

For a new requirement:

1. Establish the outcome, non-goals, data flow, compatibility needs, and observable acceptance criteria.
2. Choose the smallest design consistent with current architecture; avoid unrelated refactors and dependencies.
3. Split work into ordered, independently verifiable Tasks. A Task defaults to **1–3 primary implementation files**. If more than three are expected, split it. An exception is allowed only for an indivisible transaction, interface migration, or atomic data flow; record the reason in the Task Spec.
4. Assign mandatory priority (`P0`–`P3`) and difficulty (`Low`, `Medium`, `High`). Priority controls urgency; difficulty controls execution capability. Do not infer one from the other.
5. Create/update `docs/tasks/TASK-XXX.md` and register status and sequencing in `docs/TASK_LIST.md`. Mark only tasks with satisfied prerequisites `READY`; later tasks remain `DRAFT`.
6. Update architecture documentation only when effective architecture changes; use an ADR for consequential or hard-to-reverse decisions.
7. Before dispatch, create an Execution Capsule from confirmed facts. The Task Spec is only its `planning_source`, not the executor's default reading assignment.

Priority meanings: `P0` emergency/security/data-loss/release blocker; `P1` milestone critical path or material near-term risk; `P2` normal planned work (default); `P3` optional/deferred improvement.

Difficulty meanings: `Low` explicit low-risk established pattern; `Medium` localized design/diagnosis with moderate interactions; `High` cross-module state/data flow, migration, auth/security, concurrency, performance, unfamiliar code, or substantial judgment.

Never put implementation-agent, model, or vendor names in shared planning artifacts.

## Context-efficiency acceptance

A handoff is acceptable only when:

- A new executor can begin after reading the capsule once and only its listed source anchors.
- It need not read an entire prerequisite Task Spec or review history.
- After context compaction it need only reread the capsule and currently modified files.
- The responsible reviewer can see the file boundary and verification ceiling directly from the capsule.
- Growth of Review Records does not increase future capsule or dispatch-prompt length.

If confirmed facts cannot support these properties, do not dispatch. Resolve the missing planning facts or split the Task.

For a deterministic structure check, run `python3 scripts/validate_handoff_artifacts.py` in `planning`, `dispatch`, `review`, or explicit `legacy` mode. This validator complements review judgment; it does not invent missing facts.

## Review mode

Review supplied diffs, errors, tests, or Implementation Reports for architecture alignment, correctness, boundary handling, types, state transitions, security, resource lifecycle, compatibility, scope discipline, and evidence against acceptance criteria.

Return exactly one verdict: `[PASSED]`, `[PASSED_WITH_NOTES]`, `[CHANGES_REQUESTED]`, or `[BLOCKED]`.

- Always create a separate Review Record for the attempt; keep historical findings out of the Task Spec.
- On `[CHANGES_REQUESTED]`, keep the Task open and create a **delta capsule** for the next attempt containing only unresolved active findings. Preserve accepted implementation, narrow the file allowlist and verification scope, and do not resend the whole original Task.
- On `[PASSED]` or `[PASSED_WITH_NOTES]`, mark the Task `PASSED`, record material notes, and promote only the next unblocked Task to `READY`.
- On `[BLOCKED]`, record the required decision and emit no executable handoff.

After every verdict, reassess affected non-passed Task priorities. Record each `old → new` change and reason in the Review Record, or explicitly record `已复核，无调整`. Include the same concise result under `### 优先级复核` in chat.

## Executor handoff

Treat `### 发给执行代理的下一步指令（难度：Low|Medium|High）` as a strict machine-readable dispatch signal. Emit it only when exactly one actionable, complete Execution Capsule exists. The handoff should point to the capsule, not the full Task Spec:

```markdown
### 发给执行代理的下一步指令（难度：Medium）
> 执行 @docs/execution/TASK-XXX/attempt-NN.md。只读取胶囊列出的源码锚点，只修改白名单文件，只运行定向验证，并按胶囊格式返回精简 Implementation Report。
```

Do not emit this heading for blocked, draft, locked, incomplete, ambiguous, or no-next-task states. Its absence means `no dispatch` to automation.

The Task Spec may be read by the executor only when the capsule names an exact section under `required_planning_lookup` and explains why that section cannot be projected safely. Never tell the executor to reread `TASK_LIST`, prior Review Records, or entire prerequisite Task Specs.

## Legacy compatibility

Projects containing only `docs/tasks/TASK-XXX.md` remain valid for planning and review. Migrate lazily at the next dispatch or correction:

- Inspect current repository facts and create attempt `01` only when objective, anchors, allowlist, limits, targeted verification, and baseline are confirmed.
- Do not infer or fabricate missing allowlists, commands, baseline failures, or prerequisite contracts. Mark them `待确认` and withhold the dispatch signal until resolved.
- Existing review history may remain in an old Task Spec. Do not copy it into a capsule; new reviews go to Review Records.
- A legacy Task-Spec-only pointer is a compatibility fallback, not the preferred handoff, and must not claim capsule-level context guarantees.

## Approved Task Git sync

Automatic Git sync is opt-in via private `config.local.toml`; otherwise use disabled defaults from `config.example.toml`. Never publish the local config.

After `[PASSED]` or `[PASSED_WITH_NOTES]`, when enabled, commit only approved Task-scoped implementation, tests, required generated/migration files, the Task Spec, current capsule and Review Record, `docs/TASK_LIST.md`, and architecture/ADR changes caused by the Task. Require passed acceptance verification, a named branch, no Git operation in progress, no suspected secrets, and no unrelated staged files.

Run `python3 scripts/commit_and_sync_task.py` with explicit `--spec`, `--capsule`, `--review`, passing acceptance `--verification` records, and an explicit `--path` for every approved file. The helper must validate the complete review bundle before staging. Use subject `task(TASK-XXX): <short title>` and report commit SHA, branch, paths, and push status. Push only to the current branch's existing upstream when enabled. Never create upstreams, force-push, amend, rewrite history, switch branches, merge, or open a PR. Preserve a local commit when push fails; do not retry automatically.

Complete configured sync before selecting the next Task. A sync blocker does not change the review verdict.

## Channel adapters

The core skill stops at a vendor-neutral capsule and review state. Dispatch, authentication, process recovery, model flags, and channel permissions belong to adapters. Any downstream agent may execute a capsule when its capabilities match the recorded difficulty and the user or dispatch system authorizes that channel.

- For an explicitly authorized Cursor CLI dispatch, read [references/adapters/cursor-cli.md](references/adapters/cursor-cli.md). Do not load it for ordinary planning or review.
- Other channels require their own adapter. Do not embed their model behavior in Task Specs or capsules.

## Response shape

Keep planning and review chat responses compact. Report the Task ID/status, priority, difficulty, relevant artifact paths, constraints, and targeted verification. The repository artifacts carry detail.

When the user asks for an artifact definition or migration explanation, report the three responsibility boundaries and compatibility behavior explicitly. When exactly one actionable capsule exists, append the machine-readable handoff heading above; otherwise omit it entirely.
