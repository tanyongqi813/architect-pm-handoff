# Task Spec contract

Read this reference only when creating, migrating, or validating a Task Spec.

## Boundary

A Task Spec contains durable planning facts. It must not accumulate attempt instructions, implementation transcripts, command output, Implementation Reports, review verdict history, or resolved findings. Current status and the active attempt pointer may live in compact metadata or `docs/TASK_LIST.md`.

Expected primary implementation scope is 1–3 files. When more than three are unavoidable because of an indivisible transaction, interface migration, or atomic data flow, record the exception reason. This is a planning estimate, not the executor's file allowlist; the exact allowlist belongs in the Execution Capsule.

Do not name an executor product, model, or vendor. Record only difficulty and capability-relevant constraints.

## Template

```markdown
# TASK-XXX — [长期任务标题]

- status: `DRAFT | READY | IN_PROGRESS | PASSED | BLOCKED`
- priority: `P0 | P1 | P2 | P3`
- difficulty: `Low | Medium | High`
- dependencies: `[TASK-YYY] | none`
- current_attempt: `NN | none`

## 业务结果
[完成后可观察到的业务结果。]

## 非目标
- [明确不在本 Task 内解决的事项。]

## 架构设计
[稳定的技术路径、数据流和模块边界。]

## 兼容要求
- [必须保持的接口、数据或行为兼容性。]

## 验收标准
- [与实现方式解耦、可观察的完成条件。]

## 依赖与排序
- [前置 Task、外部决策或 `none`。]

## 主要接口
- `path/module` — `Type.symbol` / protocol / schema: [长期契约。]

## 长期约束
- [跨 attempt 仍成立的安全、性能、数据或架构约束。]

## 微批边界
- expected_primary_files: `1–3`
- exception_reason: `none` 或 [不可拆分理由]
```

## Forbidden content

Put the following elsewhere:

- Per-attempt objective, exact file allowlist, exact commands, known baseline failures, and report format → Execution Capsule.
- Verdicts, findings, raw evidence, priority reassessment history, and next correction state → Review Record.
- CLI flags, authentication, recovery, timeout, or model behavior → channel adapter.
