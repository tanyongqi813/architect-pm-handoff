# Review Record contract

Read this reference only when recording, validating, or explaining a review.

## Purpose and location

Use one immutable record per attempt: `docs/reviews/TASK-XXX/attempt-NN.md`. The record preserves evidence and history for planners/reviewers without enlarging later execution prompts. A future capsule reads only the latest unresolved finding IDs, not the full history.

## Template

```markdown
# Review Record — TASK-XXX / attempt-NN

- task_id: `TASK-XXX`
- attempt: `NN`
- capsule: `docs/execution/TASK-XXX/attempt-NN.md` or `legacy-task-spec-only`
- reviewed_at: `YYYY-MM-DD`
- verdict: `PASSED | PASSED_WITH_NOTES | CHANGES_REQUESTED | BLOCKED`
- reviewer_role: `lead-ai`

## 审查范围
- implementation_report: [path/link/inline source]
- diff_scope: [reviewed paths or commit]
- acceptance_slice: [criteria evaluated this attempt]

## 验证证据
- `[command/check]` → `PASS | FAIL | NOT_RUN`: [concise evidence]

## Findings
- `F-01` — `active | resolved | accepted_note`; severity: `blocking | non_blocking`; anchor: `path::symbol`; [problem and required outcome]

## 架构与范围结论
- alignment: [concise result]
- scope: [within capsule / deviation]
- preserved_behavior: [important accepted behavior]

## 优先级复核
- `已复核，无调整`, or `TASK-XXX P2 → P1`: [reason]

## 下一状态
- task_status: `READY_FOR_CORRECTION | PASSED | BLOCKED`
- next_action: `none | correction | checkpoint_resume`
- next_capsule: `docs/execution/TASK-XXX/attempt-NEXT.md | none`
- active_findings_for_next_attempt: `F-01,F-02 | none`
```

## Rules

- Give finding IDs stable meaning within the Task. Never reuse an ID for a different defect.
- The next correction capsule carries only `active` findings; do not copy resolved findings or review narrative.
- A `PASSED_WITH_NOTES` note is not silently converted into future execution work. Create a new planned Task only if accepted and prioritized.
- Keep raw logs and large diffs outside the record; link or summarize evidence.
- Do not append repeated reviews to the Task Spec. For legacy specs with embedded history, leave existing content intact and start Review Records at the next review.
- `reviewer_role` is `lead-ai`; host or vendor names do not replace the protocol role.
- `PASSED` and `PASSED_WITH_NOTES` require `task_status: PASSED`, passing verification evidence, `next_capsule: none`, and no active findings.
- `CHANGES_REQUESTED` with `next_action: correction` requires `task_status: READY_FOR_CORRECTION`, at least one active finding, and a next-attempt delta Capsule with `revision_reason: changes_requested` containing exactly those finding IDs.
- `CHANGES_REQUESTED` with `next_action: checkpoint_resume` requires `task_status: READY_FOR_CORRECTION`, no manufactured active finding, and a next-attempt Capsule with `revision_reason: checkpoint_resume`. Remaining checkpoint gaps live in that Capsule's objective and acceptance slice.
- `PASSED`, `PASSED_WITH_NOTES`, and `BLOCKED` use `next_action: none`.
- Historical Review Records without `next_action` remain readable with legacy Capsules; every schema 2 review must state it explicitly.
- `BLOCKED` requires `task_status: BLOCKED` and no executable next Capsule or next-attempt active findings.
- A budget-exhausted `partial + checkpoint` is reviewed against the actual diff. It normally leads to a scoped `CHANGES_REQUESTED`/`checkpoint_resume` cycle, not `BLOCKED`; the executor's summary alone cannot establish acceptance.
