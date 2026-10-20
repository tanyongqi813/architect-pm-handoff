from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "dispatch_cursor_cli.py"


TASK = """# TASK-001 — Dispatch guard

- status: `READY`
- priority: `P2`
- difficulty: `Low`
- dependencies: `none`
- current_attempt: `01`

## 业务结果
Guard dispatch.
## 非目标
- Other work.
## 架构设计
Validate before launch.
## 兼容要求
- Preserve legacy mode.
## 验收标准
- Invalid capsule does not launch.
## 依赖与排序
- none
## 主要接口
- `src/app.py` — `run`
## 长期约束
- No added permission.
## 微批边界
- expected_primary_files: `1`
- exception_reason: `none`
"""


BAD_CAPSULE = """# Execution Capsule — TASK-001 / attempt-01

- planning_source: `docs/tasks/TASK-001.md`
- task_id: `TASK-001`
- attempt: `01`
- revision_reason: `initial`
- priority: `P2`
- difficulty: `Low`
- required_planning_lookup: `none`

## 本轮唯一目标
待确认
## 已确认事实（禁止重新推导）
- Guard exists.
## Active findings
- none
## 源码锚点（最多 5 个）
1. `src/app.py` — `run`
## 修改白名单
- `src/app.py`
- max_modified_files: `1`
## 明确非目标
- Other work.
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


class DispatchGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        (self.repo / "docs/tasks").mkdir(parents=True)
        (self.repo / "docs/execution/TASK-001").mkdir(parents=True)
        (self.repo / "docs/tasks/TASK-001.md").write_text(TASK, encoding="utf-8")
        (self.repo / "docs/execution/TASK-001/attempt-01.md").write_text(
            BAD_CAPSULE, encoding="utf-8"
        )
        self.marker = self.repo / "agent-launched"
        self.agent = self.repo / "fake-agent"
        self.agent.write_text(
            f"#!/bin/sh\nprintf launched > '{self.marker}'\n", encoding="utf-8"
        )
        self.agent.chmod(0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_bad_capsule_does_not_launch_cursor(self) -> None:
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "--repo", str(self.repo),
                "--capsule", "docs/execution/TASK-001/attempt-01.md",
                "--agent-command", str(self.agent), "--dry-run",
            ],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Capsule validation failed", result.stderr)
        self.assertFalse(self.marker.exists(), "fake Cursor agent was launched")

    def test_unsafe_planning_source_does_not_launch_cursor(self) -> None:
        path = self.repo / "docs/execution/TASK-001/attempt-01.md"
        path.write_text(
            BAD_CAPSULE.replace(
                "`docs/tasks/TASK-001.md`", "`../../outside-task.md`"
            ).replace("待确认", "Guard dispatch."),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "--repo", str(self.repo),
                "--capsule", "docs/execution/TASK-001/attempt-01.md",
                "--agent-command", str(self.agent), "--dry-run",
            ],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("planning_source escapes repository", result.stderr)
        self.assertFalse(self.marker.exists(), "fake Cursor agent was launched")

    def test_legacy_task_keeps_compatibility_semantics(self) -> None:
        legacy = self.repo / "docs/tasks/LEGACY.md"
        legacy.write_text("# Legacy free-form task\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "--repo", str(self.repo),
                "--task", "docs/tasks/LEGACY.md",
                "--agent-command", str(self.agent), "--dry-run",
            ],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("旧版任务说明", result.stdout)
        self.assertIn("不推导缺失", result.stdout)
        self.assertFalse(self.marker.exists(), "fake Cursor agent was launched")


if __name__ == "__main__":
    unittest.main()
