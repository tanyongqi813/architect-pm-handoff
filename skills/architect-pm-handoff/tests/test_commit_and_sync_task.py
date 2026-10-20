from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "commit_and_sync_task.py"


TASK = """# TASK-001 — Sync guard

- status: `PASSED`
- priority: `P1`
- difficulty: `Medium`
- dependencies: `none`
- current_attempt: `01`

## 业务结果
Approved changes are traceable.
## 非目标
- Unrelated files.
## 架构设计
Validate before staging.
## 兼容要求
- Keep Git safety checks.
## 验收标准
- Invalid review package leaves index unchanged.
## 依赖与排序
- none
## 主要接口
- `src/app.py` — `run`
## 长期约束
- No force push.
## 微批边界
- expected_primary_files: `1`
- exception_reason: `none`
"""

CAPSULE = """# Execution Capsule — TASK-001 / attempt-01

- planning_source: `docs/tasks/TASK-001.md`
- task_id: `TASK-001`
- attempt: `01`
- revision_reason: `initial`
- priority: `P1`
- difficulty: `Medium`
- required_planning_lookup: `none`

## 本轮唯一目标
Implement sync guard.
## 已确认事实（禁止重新推导）
- Existing Git safety stays.
## Active findings
- none
## 源码锚点（最多 5 个）
1. `src/app.py` — `run`
## 修改白名单
- `src/app.py`
- max_modified_files: `1`
## 明确非目标
- Unrelated files.
## 定向验证（最多 5 条）
1. `python -m unittest test_app` — PASS
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
- verification: results
- active_findings: status
- scope_or_baseline_notes: facts
"""

REVIEW = """# Review Record — TASK-001 / attempt-01

- task_id: `TASK-001`
- attempt: `01`
- capsule: `docs/execution/TASK-001/attempt-01.md`
- reviewed_at: `2026-10-20`
- verdict: `PASSED`
- reviewer_role: `lead-ai`

## 审查范围
- implementation_report: inline
- diff_scope: src/app.py
- acceptance_slice: sync guard
## 验证证据
- `python -m unittest test_app` → PASS
## Findings
- none
## 架构与范围结论
- alignment: aligned
- scope: within capsule
- preserved_behavior: Git safety
## 优先级复核
- 已复核，无调整
## 下一状态
- task_status: `PASSED`
- next_capsule: `none`
- active_findings_for_next_attempt: `none`
"""


class CommitSyncGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.run(
            ["git", "init", "-b", "main"], cwd=self.repo,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        for directory in (
            "docs/tasks", "docs/execution/TASK-001", "docs/reviews/TASK-001", "src"
        ):
            (self.repo / directory).mkdir(parents=True, exist_ok=True)
        (self.repo / "docs/tasks/TASK-001.md").write_text(TASK, encoding="utf-8")
        (self.repo / "docs/execution/TASK-001/attempt-01.md").write_text(CAPSULE, encoding="utf-8")
        (self.repo / "docs/reviews/TASK-001/attempt-01.md").write_text(REVIEW, encoding="utf-8")
        (self.repo / "src/app.py").write_text("def run(): return True\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def index_state(self) -> str:
        return subprocess.run(
            ["git", "diff", "--cached", "--binary"], cwd=self.repo, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        ).stdout

    def command(self) -> list[str]:
        return [
            sys.executable, str(SCRIPT), "--repo", str(self.repo),
            "--task-id", "TASK-001", "--title", "Sync guard",
            "--spec", "docs/tasks/TASK-001.md",
            "--capsule", "docs/execution/TASK-001/attempt-01.md",
            "--review", "docs/reviews/TASK-001/attempt-01.md",
            "--verdict", "PASSED", "--priority", "P1", "--difficulty", "Medium",
            "--verification", "python -m unittest test_app → PASS",
            "--path", "docs/tasks/TASK-001.md",
            "--path", "docs/execution/TASK-001/attempt-01.md",
            "--path", "docs/reviews/TASK-001/attempt-01.md",
            "--path", "src/app.py", "--dry-run",
        ]

    def assert_rejected_without_index_change(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        before = self.index_state()
        result = subprocess.run(
            command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.index_state(), before)
        return result

    def test_valid_package_dry_run_does_not_stage(self) -> None:
        before = self.index_state()
        result = subprocess.run(
            self.command(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.index_state(), before)

    def test_missing_review_is_rejected_before_staging(self) -> None:
        command = self.command()
        index = command.index("--review")
        del command[index:index + 2]
        self.assert_rejected_without_index_change(command)

    def test_wrong_review_verdict_is_rejected_before_staging(self) -> None:
        review = self.repo / "docs/reviews/TASK-001/attempt-01.md"
        review.write_text(
            REVIEW.replace("- verdict: `PASSED`", "- verdict: `PASSED_WITH_NOTES`"),
            encoding="utf-8",
        )
        result = self.assert_rejected_without_index_change(self.command())
        self.assertIn("--verdict does not match Review Record", result.stderr)

    def test_missing_verification_is_rejected_before_staging(self) -> None:
        command = self.command()
        index = command.index("--verification")
        del command[index:index + 2]
        self.assert_rejected_without_index_change(command)

    def test_review_without_pass_evidence_is_rejected_before_staging(self) -> None:
        review = self.repo / "docs/reviews/TASK-001/attempt-01.md"
        review.write_text(
            REVIEW.replace("`python -m unittest test_app` → PASS", "verification omitted"),
            encoding="utf-8",
        )
        result = self.assert_rejected_without_index_change(self.command())
        self.assertIn("PASS verification evidence", result.stderr)


if __name__ == "__main__":
    unittest.main()
