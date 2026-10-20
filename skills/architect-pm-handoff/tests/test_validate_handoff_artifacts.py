from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_handoff_artifacts.py"


TASK = """# TASK-016 — Refresh coalescing

- status: `READY`
- priority: `P1`
- difficulty: `Medium`
- dependencies: `none`
- current_attempt: `02`

## 业务结果
Concurrent 401 responses share one refresh.
## 非目标
- Token storage.
## 架构设计
Reuse one in-flight promise.
## 兼容要求
- Preserve request return types.
## 验收标准
- One refresh for concurrent failures.
## 依赖与排序
- none
## 主要接口
- `src/auth.ts` — `Auth.refresh`
## 长期约束
- No new dependency.
## 微批边界
- expected_primary_files: `2`
- exception_reason: `none`
"""

CAPSULE = """# Execution Capsule — TASK-016 / attempt-02

- planning_source: `docs/tasks/TASK-016.md`
- task_id: `TASK-016`
- attempt: `02`
- revision_reason: `changes_requested`
- priority: `P1`
- difficulty: `Medium`
- required_planning_lookup: `none`

## 本轮唯一目标
Coalesce refresh.
## 已确认事实（禁止重新推导）
- Existing retry stays.
## Active findings
- `F-02`: duplicate refresh.
## 源码锚点（最多 5 个）
1. `src/auth.ts` — `Auth.refresh`
2. `tests/auth.test.ts` — `coalesces refresh`
## 修改白名单
- `src/auth.ts`
- `tests/auth.test.ts`
- max_modified_files: `2`
## 明确非目标
- Accepted behavior stays unchanged.
## 定向验证（最多 5 条）
1. `pytest tests/auth.test.ts` — passes
## 禁止验证
- No full suite.
## 已知基线失败
- none confirmed
## 停止条件
- Scope expands.
## 精简 Implementation Report（固定格式）
- outcome: completed | blocked
- changed_files: paths
- anchors_touched: symbols
- verification: command results
- active_findings: finding status
- scope_or_baseline_notes: new facts
"""

REVIEW = """# Review Record — TASK-016 / attempt-02

- task_id: `TASK-016`
- attempt: `02`
- capsule: `docs/execution/TASK-016/attempt-02.md`
- reviewed_at: `2026-10-20`
- verdict: `PASSED`
- reviewer_role: `lead-ai`

## 审查范围
- current diff
## 验证证据
- `pytest tests/auth.test.ts` → PASS
## Findings
- F-02 resolved
## 架构与范围结论
- aligned
## 优先级复核
- 已复核，无调整
## 下一状态
- task_status: `PASSED`
- next_capsule: `none`
- active_findings_for_next_attempt: `none`
"""


class ArtifactValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        (self.repo / "docs/tasks").mkdir(parents=True)
        (self.repo / "docs/execution/TASK-016").mkdir(parents=True)
        (self.repo / "docs/reviews/TASK-016").mkdir(parents=True)
        (self.repo / "docs/tasks/TASK-016.md").write_text(TASK, encoding="utf-8")
        (self.repo / "docs/execution/TASK-016/attempt-02.md").write_text(CAPSULE, encoding="utf-8")
        (self.repo / "docs/reviews/TASK-016/attempt-02.md").write_text(REVIEW, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_validator(self, mode: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), "--mode", mode,
             "--task", "docs/tasks/TASK-016.md", *extra],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def test_review_bundle_passes(self) -> None:
        result = self.run_validator(
            "review", "--capsule", "docs/execution/TASK-016/attempt-02.md",
            "--review", "docs/reviews/TASK-016/attempt-02.md"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "PASS")

    def test_task_rejects_embedded_review_history(self) -> None:
        path = self.repo / "docs/tasks/TASK-016.md"
        path.write_text(TASK + "\n## Review History\n- old verdict\n", encoding="utf-8")
        result = self.run_validator("planning")
        self.assertEqual(result.returncode, 2)
        self.assertIn("execution/review headings", result.stdout)

    def test_capsule_rejects_more_than_five_anchors(self) -> None:
        path = self.repo / "docs/execution/TASK-016/attempt-02.md"
        text = CAPSULE.replace(
            "2. `tests/auth.test.ts` — `coalesces refresh`",
            "2. `tests/auth.test.ts` — `coalesces refresh`\n3. `a` — `a`\n4. `b` — `b`\n5. `c` — `c`\n6. `d` — `d`",
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator(
            "dispatch", "--capsule", "docs/execution/TASK-016/attempt-02.md"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("1–5 source anchors", result.stdout)

    def test_legacy_mode_does_not_invent_projection(self) -> None:
        (self.repo / "docs/tasks/TASK-016.md").write_text(
            "# TASK-016\n\nOld free-form task without capsule fields.\n", encoding="utf-8"
        )
        result = self.run_validator("legacy")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dispatch_rejects_unresolved_capsule_facts(self) -> None:
        path = self.repo / "docs/execution/TASK-016/attempt-02.md"
        path.write_text(CAPSULE.replace("- none confirmed", "- 待确认"), encoding="utf-8")
        result = self.run_validator(
            "dispatch", "--capsule", "docs/execution/TASK-016/attempt-02.md"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unresolved facts", result.stdout)

    def test_task_rejects_vendor_bound_executor(self) -> None:
        path = self.repo / "docs/tasks/TASK-016.md"
        path.write_text(TASK + "\n执行者: Cursor\n", encoding="utf-8")
        result = self.run_validator("planning")
        self.assertEqual(result.returncode, 2)
        self.assertIn("vendor/model", result.stdout)

    def test_review_rejects_invalid_verdict(self) -> None:
        path = self.repo / "docs/reviews/TASK-016/attempt-02.md"
        path.write_text(REVIEW.replace("- verdict: `PASSED`", "- verdict: `APPROVED`"), encoding="utf-8")
        result = self.run_validator(
            "review", "--capsule", "docs/execution/TASK-016/attempt-02.md",
            "--review", "docs/reviews/TASK-016/attempt-02.md"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid verdict", result.stdout)

    def test_review_rejects_wrong_status_combination(self) -> None:
        path = self.repo / "docs/reviews/TASK-016/attempt-02.md"
        path.write_text(
            REVIEW.replace("- task_status: `PASSED`", "- task_status: `READY_FOR_CORRECTION`"),
            encoding="utf-8",
        )
        result = self.run_validator(
            "review", "--capsule", "docs/execution/TASK-016/attempt-02.md",
            "--review", "docs/reviews/TASK-016/attempt-02.md"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("task_status to PASSED", result.stdout)

    def test_review_rejects_mismatched_attempt(self) -> None:
        path = self.repo / "docs/reviews/TASK-016/attempt-02.md"
        path.write_text(REVIEW.replace("- attempt: `02`", "- attempt: `03`"), encoding="utf-8")
        result = self.run_validator(
            "review", "--capsule", "docs/execution/TASK-016/attempt-02.md",
            "--review", "docs/reviews/TASK-016/attempt-02.md"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("attempt does not match Capsule", result.stdout)

    def test_changes_requested_requires_matching_next_delta(self) -> None:
        next_capsule = CAPSULE.replace("attempt-02", "attempt-03").replace(
            "- attempt: `02`", "- attempt: `03`"
        )
        (self.repo / "docs/execution/TASK-016/attempt-03.md").write_text(
            next_capsule, encoding="utf-8"
        )
        changes = REVIEW.replace("- verdict: `PASSED`", "- verdict: `CHANGES_REQUESTED`")
        changes = changes.replace("- F-02 resolved", "- F-02 active")
        changes = changes.replace(
            "- task_status: `PASSED`\n- next_capsule: `none`\n- active_findings_for_next_attempt: `none`",
            "- task_status: `READY_FOR_CORRECTION`\n"
            "- next_capsule: `docs/execution/TASK-016/attempt-03.md`\n"
            "- active_findings_for_next_attempt: `F-02`",
        )
        (self.repo / "docs/reviews/TASK-016/attempt-02.md").write_text(changes, encoding="utf-8")
        result = self.run_validator(
            "review", "--capsule", "docs/execution/TASK-016/attempt-02.md",
            "--review", "docs/reviews/TASK-016/attempt-02.md"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
