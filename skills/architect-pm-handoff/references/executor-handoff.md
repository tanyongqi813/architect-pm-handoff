# Execution Capsule contract

Read this reference only when creating, revising, validating, or explaining an Execution Capsule.

## Purpose and location

An Execution Capsule is the bounded contract for one implementation attempt. Prefer `docs/execution/TASK-XXX/attempt-NN.md`; use the repository's established equivalent when one exists. Capsules are vendor-neutral and immutable after dispatch except for correcting a factual typo before work begins. A new implementation or correction attempt gets a new number.

## Limits

- New implementation: target 1,500–2,000 Chinese characters.
- Ordinary correction: target 800–1,200 Chinese characters.
- At most five source anchors and five verification commands.
- Default to 1–3 primary implementation files. State `max_modified_files` explicitly.
- State one acceptance slice and one-attempt budget. Budgets in a capsule are planning ceilings unless an adapter confirms a runner-enforced limit.
- If the contract cannot fit without losing safety or clarity, split the Task instead of enlarging the capsule.

Source anchors should name `path + function/type/test/symbol`. Use line numbers only as a non-authoritative hint. Every command must be targeted to this attempt. Explicitly list prohibited full-suite, build, UI, integration, or repeated verification when they are not required.

## Template

```markdown
# Execution Capsule — TASK-XXX / attempt-NN

- planning_source: `docs/tasks/TASK-XXX.md`
- task_id: `TASK-XXX`
- attempt: `NN`
- revision_reason: `initial | changes_requested | checkpoint_resume`
- priority: `P0|P1|P2|P3`
- difficulty: `Low|Medium|High`
- required_planning_lookup: `none` or an exact heading plus reason
- capsule_schema: `2`

## 本轮唯一目标
[One observable outcome.]

## 本轮验收切片
- [The smallest acceptance criterion this attempt can finish and prove.]

## 已确认事实（禁止重新推导）
- [Fact or accepted contract.]

## Active findings
- `F-01`: [Only unresolved finding; use `none` for initial implementation.]

## 源码锚点（最多 5 个）
1. `path/to/file.ext` — `Type.function` / `test_name`: [why it matters]

## 修改白名单
- `path/to/file.ext`
- max_modified_files: `N`

## 明确非目标
- [Behavior/file/refactor that must remain unchanged.]
- For a correction: 已通过和未被 active finding 指向的现有实现保持不动。

## 定向验证（最多 5 条）
1. `[exact command]` — [expected evidence]

## 禁止验证
- Do not run `[full suite/build/UI/integration command or category]`.
- Do not repeat a passing command unless code affecting it changed after the pass.

## 已知基线失败
- `[command/test]`: [confirmed failure and why it is out of scope], or `none confirmed`.

## 单次执行预算
- budget_mode: `prompt_soft | runner_enforced | mixed`
- soft_timebox_minutes: `N | none`
- soft_call_limit: `N | none`
- runner_limit_reference: `adapter-owned identifier | none`
- max_correction_rounds: `1`
- on_budget_stop: `return partial + checkpoint; do not claim completed or blocked`

`prompt_soft` only instructs the executor to stop and cannot terminate a process. `runner_enforced` is valid only when the selected channel adapter actually enforces the named limit. Never claim that remaining quota can be predicted exactly.

## 停止条件
- A required change falls outside the allowlist or exceeds `max_modified_files`.
- Repository behavior conflicts with this capsule or the named planning contract.
- A product/architecture decision, new permission, credential, or destructive action is required.
- Targeted verification cannot run or reveals impact outside scope.

## 精简 Implementation Report（固定格式）
- outcome: `completed | partial | blocked`
- handoff: `none | checkpoint`
- stop_reason: `none | soft_budget | runner_limit | context_limit | external_decision | permission | scope_conflict`
- workspace_branch: `[absolute workspace or worktree] @ [branch or detached SHA]`
- changed_files: [paths only]
- completed_scope: [observable work completed]
- remaining_gaps: [specific unfinished work; `none` only when completed]
- anchors_touched: [symbols/tests only]
- verification: [command → PASS/FAIL/NOT_RUN; latest_code_covered: yes/no]
- active_findings: [finding id → resolved/unresolved]
- scope_or_baseline_notes: [new fact only; no transcript]
```

## Projection rules

Project only confirmed, execution-relevant facts from the Task Spec and current code. Do not copy long rationale, completed findings, prior transcripts, or all acceptance criteria. Translate the relevant acceptance slice into this attempt's objective and targeted verification.

`required_planning_lookup` defaults to `none`. Use it only for an exact, stable section whose full semantics cannot be safely shortened, such as a normative protocol table. Never point to an entire file.

For `[CHANGES_REQUESTED]`, create a delta capsule: carry only unresolved finding IDs; preserve accepted implementation; reduce anchors, allowlist, file limit, and verification; do not repeat the original narrative or already-passing checks.

For a budget stop, the executor returns `outcome: partial` and `handoff: checkpoint`. The lead must inspect the actual diff and verification freshness before deciding what is accepted. If more work is justified, create the next immutable capsule with `revision_reason: checkpoint_resume`, projecting only remaining gaps and newly confirmed code facts. Do not resend the original capsule or require rereading the Task Spec, prior Review Records, or already inspected anchors.

An adapter should permit at most the initial execution plus one bounded correction by default. If the acceptance slice is still incomplete, stop automation and return control to the lead for diff review and a new incremental capsule. A prompt budget is never described as a process-level enforcement mechanism.

## Complete correction example

```markdown
# Execution Capsule — TASK-016 / attempt-02

- planning_source: `docs/tasks/TASK-016.md`
- task_id: `TASK-016`
- attempt: `02`
- revision_reason: `changes_requested`
- priority: `P1`
- difficulty: `Medium`
- required_planning_lookup: `none`
- capsule_schema: `2`

## 本轮唯一目标
修复刷新令牌并发请求在首次 401 后触发多次 refresh 的问题，保证同一会话最多存在一个 refresh 请求，其余请求复用结果。

## 本轮验收切片
- 并发 401 只发起一次 refresh，且 refresh 失败后下一次请求可以重新发起。

## 已确认事实（禁止重新推导）
- `AuthClient.request` 已负责 401 后的一次重试；该行为和公开返回类型保持不变。
- 当前缺陷仅发生在并发 401 汇合处，不需要修改令牌存储接口。
- attempt-01 的请求封装、错误映射和非 401 路径已经评审通过。

## Active findings
- `F-02`: `refreshToken()` 缺少 in-flight promise 复用，三个并发 401 会发出三个 refresh 请求。

## 源码锚点（最多 5 个）
1. `src/auth/auth-client.ts` — `AuthClient.refreshToken`: 引入并清理单例 in-flight promise。
2. `src/auth/auth-client.ts` — `AuthClient.request`: 只验证既有重试路径复用 refresh 结果，不重写错误映射。
3. `tests/auth/auth-client.test.ts` — `coalesces concurrent refresh requests`: 覆盖并发 401 和失败清理。

## 修改白名单
- `src/auth/auth-client.ts`
- `tests/auth/auth-client.test.ts`
- max_modified_files: `2`

## 明确非目标
- 不修改 token store、HTTP transport、公开类型或错误文案。
- 已通过和未被 `F-02` 指向的现有实现保持不动。

## 定向验证（最多 5 条）
1. `pnpm vitest tests/auth/auth-client.test.ts -t "coalesces concurrent refresh requests"` — 并发成功路径只调用一次 refresh。
2. `pnpm vitest tests/auth/auth-client.test.ts -t "clears failed refresh"` — refresh 失败后允许下一次请求重新发起。
3. `pnpm tsc --noEmit --pretty false --incremental false` — 两个修改文件未引入类型错误。

## 禁止验证
- 不运行全量 `pnpm test`、端到端测试、UI 测试或生产构建。
- 某条命令已通过后，除非其覆盖代码再次变化，否则不重复运行。

## 已知基线失败
- `pnpm test`: 存在与本任务无关的 `timezone snapshot` 基线失败；本轮禁止用全量测试复核。

## 单次执行预算
- budget_mode: `prompt_soft`
- soft_timebox_minutes: `30`
- soft_call_limit: `12`
- runner_limit_reference: `none`
- max_correction_rounds: `1`
- on_budget_stop: `return partial + checkpoint; do not claim completed or blocked`

## 停止条件
- 修复需要修改 token store 或第三个实现文件。
- 发现 401 重试契约与已确认事实冲突。
- 需要新增依赖、凭据或网络权限。
- 定向测试暴露非并发刷新范围的回归。

## 精简 Implementation Report（固定格式）
- outcome: `completed | partial | blocked`
- handoff: `none | checkpoint`
- stop_reason: `none | soft_budget | runner_limit | context_limit | external_decision | permission | scope_conflict`
- workspace_branch: `[absolute workspace or worktree] @ [branch or detached SHA]`
- changed_files: [paths only]
- completed_scope: [observable work completed]
- remaining_gaps: [specific unfinished work]
- anchors_touched: [symbols/tests only]
- verification: [command → PASS/FAIL/NOT_RUN; latest_code_covered: yes/no]
- active_findings: [`F-02` → resolved/unresolved]
- scope_or_baseline_notes: [new fact only; no transcript]
```

## Checkpoint continuation example

After an executor reports a budget stop, the lead first inspects the workspace diff. If the implementation is incomplete but safe to continue, create the next attempt as a delta:

```markdown
# Execution Capsule — TASK-016 / attempt-03

- planning_source: `docs/tasks/TASK-016.md`
- task_id: `TASK-016`
- attempt: `03`
- revision_reason: `checkpoint_resume`
- priority: `P1`
- difficulty: `Medium`
- required_planning_lookup: `none`
- capsule_schema: `2`

## 本轮唯一目标
补齐失败 refresh 后清理 in-flight promise 的剩余分支；保留 attempt-02 已完成的并发复用逻辑。

## 本轮验收切片
- 失败 refresh 清理状态，下一次请求可以重新发起一次 refresh。

## 已确认事实（禁止重新推导）
- 负责人已检查 attempt-02 diff：并发成功路径已实现且保持不动。
- checkpoint 中的类型检查覆盖最新代码；失败清理测试尚未运行。

## Active findings
- none; this attempt continues only the reviewed checkpoint gap.

## 源码锚点（最多 5 个）
1. `src/auth/auth-client.ts` — `AuthClient.refreshToken`: 只补失败清理分支。
2. `tests/auth/auth-client.test.ts` — `clears failed refresh`: 补齐并运行该定向测试。

## 修改白名单
- `src/auth/auth-client.ts`
- `tests/auth/auth-client.test.ts`
- max_modified_files: `2`

## 明确非目标
- 不改动已评审通过的并发成功路径、token store 或公开类型。

## 定向验证（最多 5 条）
1. `pnpm vitest tests/auth/auth-client.test.ts -t "clears failed refresh"` — PASS。

## 禁止验证
- 不重复已覆盖最新代码的类型检查；不运行全量测试或构建。

## 已知基线失败
- none confirmed

## 单次执行预算
- budget_mode: `prompt_soft`
- soft_timebox_minutes: `20`
- soft_call_limit: `8`
- runner_limit_reference: `none`
- max_correction_rounds: `1`
- on_budget_stop: `return partial + checkpoint; do not claim completed or blocked`

## 停止条件
- 需要修改白名单外文件，或发现已接受的成功路径必须重写。

## 精简 Implementation Report（固定格式）
- outcome: `completed | partial | blocked`
- handoff: `none | checkpoint`
- stop_reason: `none | soft_budget | runner_limit | context_limit | external_decision | permission | scope_conflict`
- workspace_branch: `[absolute workspace or worktree] @ [branch or detached SHA]`
- changed_files: [paths only]
- completed_scope: [observable work completed]
- remaining_gaps: [specific unfinished work]
- anchors_touched: [symbols/tests only]
- verification: [command → PASS/FAIL/NOT_RUN; latest_code_covered: yes/no]
- active_findings: [finding id → resolved/unresolved]
- scope_or_baseline_notes: [new fact only]
```
