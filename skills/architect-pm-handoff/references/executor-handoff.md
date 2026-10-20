# Execution Capsule contract

Read this reference only when creating, revising, validating, or explaining an Execution Capsule.

## Purpose and location

An Execution Capsule is the bounded contract for one implementation attempt. Prefer `docs/execution/TASK-XXX/attempt-NN.md`; use the repository's established equivalent when one exists. Capsules are vendor-neutral and immutable after dispatch except for correcting a factual typo before work begins. A new implementation or correction attempt gets a new number.

## Limits

- New implementation: target 1,500–2,000 Chinese characters.
- Ordinary correction: target 800–1,200 Chinese characters.
- At most five source anchors and five verification commands.
- Default to 1–3 primary implementation files. State `max_modified_files` explicitly.
- If the contract cannot fit without losing safety or clarity, split the Task instead of enlarging the capsule.

Source anchors should name `path + function/type/test/symbol`. Use line numbers only as a non-authoritative hint. Every command must be targeted to this attempt. Explicitly list prohibited full-suite, build, UI, integration, or repeated verification when they are not required.

## Template

```markdown
# Execution Capsule — TASK-XXX / attempt-NN

- planning_source: `docs/tasks/TASK-XXX.md`
- task_id: `TASK-XXX`
- attempt: `NN`
- revision_reason: `initial | changes_requested`
- priority: `P0|P1|P2|P3`
- difficulty: `Low|Medium|High`
- required_planning_lookup: `none` or an exact heading plus reason

## 本轮唯一目标
[One observable outcome.]

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

## 停止条件
- A required change falls outside the allowlist or exceeds `max_modified_files`.
- Repository behavior conflicts with this capsule or the named planning contract.
- A product/architecture decision, new permission, credential, or destructive action is required.
- Targeted verification cannot run or reveals impact outside scope.

## 精简 Implementation Report（固定格式）
- outcome: `completed | blocked`
- changed_files: [paths only]
- anchors_touched: [symbols/tests only]
- verification: [command → PASS/FAIL/NOT_RUN]
- active_findings: [finding id → resolved/unresolved]
- scope_or_baseline_notes: [new fact only; no transcript]
```

## Projection rules

Project only confirmed, execution-relevant facts from the Task Spec and current code. Do not copy long rationale, completed findings, prior transcripts, or all acceptance criteria. Translate the relevant acceptance slice into this attempt's objective and targeted verification.

`required_planning_lookup` defaults to `none`. Use it only for an exact, stable section whose full semantics cannot be safely shortened, such as a normative protocol table. Never point to an entire file.

For `[CHANGES_REQUESTED]`, create a delta capsule: carry only unresolved finding IDs; preserve accepted implementation; reduce anchors, allowlist, file limit, and verification; do not repeat the original narrative or already-passing checks.

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

## 本轮唯一目标
修复刷新令牌并发请求在首次 401 后触发多次 refresh 的问题，保证同一会话最多存在一个 refresh 请求，其余请求复用结果。

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

## 停止条件
- 修复需要修改 token store 或第三个实现文件。
- 发现 401 重试契约与已确认事实冲突。
- 需要新增依赖、凭据或网络权限。
- 定向测试暴露非并发刷新范围的回归。

## 精简 Implementation Report（固定格式）
- outcome: `completed | blocked`
- changed_files: [paths only]
- anchors_touched: [symbols/tests only]
- verification: [command → PASS/FAIL/NOT_RUN]
- active_findings: [`F-02` → resolved/unresolved]
- scope_or_baseline_notes: [new fact only; no transcript]
```
