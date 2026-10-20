#!/usr/bin/env python3
"""Validate Task Spec, Execution Capsule, and Review Record boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


TASK_HEADINGS = {
    "业务结果",
    "非目标",
    "架构设计",
    "兼容要求",
    "验收标准",
    "依赖与排序",
    "主要接口",
    "长期约束",
    "微批边界",
}
CAPSULE_HEADINGS = {
    "本轮唯一目标",
    "已确认事实（禁止重新推导）",
    "Active findings",
    "源码锚点（最多 5 个）",
    "修改白名单",
    "明确非目标",
    "定向验证（最多 5 条）",
    "禁止验证",
    "已知基线失败",
    "停止条件",
    "精简 Implementation Report（固定格式）",
}
REVIEW_HEADINGS = {
    "审查范围",
    "验证证据",
    "Findings",
    "架构与范围结论",
    "优先级复核",
    "下一状态",
}
TASK_FORBIDDEN_HEADINGS = {
    "执行记录",
    "Implementation Report",
    "评审历史",
    "Review History",
    "Review Record",
    "Active findings",
    "定向验证",
    "已知基线失败",
}
VENDOR_BINDING = re.compile(
    r"(?:executor|执行代理|执行者|下游(?:\s*agent)?)\s*[:：=-]?\s*"
    r"(?:codex|claude|cursor|kimi|deepseek)|"
    r"(?:codex|claude|cursor|kimi|deepseek)\s*(?:作为|is|=|:)\s*"
    r"(?:executor|执行代理|执行者|下游)",
    re.IGNORECASE,
)
ALLOWED_VERDICTS = {"PASSED", "PASSED_WITH_NOTES", "CHANGES_REQUESTED", "BLOCKED"}
ALLOWED_REVIEWER_ROLES = {"lead-ai"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Repository root")
    parser.add_argument(
        "--mode", choices=["planning", "dispatch", "review", "legacy"], required=True
    )
    parser.add_argument("--task", required=True, help="Repository-relative Task Spec")
    parser.add_argument("--capsule", help="Repository-relative Execution Capsule")
    parser.add_argument("--review", help="Repository-relative Review Record")
    return parser.parse_args()


def resolve(repo: Path, value: str, label: str) -> tuple[Path | None, str | None]:
    raw = Path(value)
    if raw.is_absolute():
        return None, f"{label} path must be repository-relative"
    path = (repo / raw).resolve()
    try:
        path.relative_to(repo)
    except ValueError:
        return None, f"{label} path escapes repository"
    if not path.is_file():
        return None, f"{label} does not exist: {value}"
    return path, None


def headings(text: str) -> set[str]:
    return {match.group(1).strip() for match in re.finditer(r"^##\s+(.+?)\s*$", text, re.M)}


def section(text: str, title: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(title)}\s*$\n(.*?)(?=^##\s+|\Z)", text, re.M | re.S
    )
    return match.group(1).strip() if match else ""


def field(text: str, key: str) -> str | None:
    match = re.search(rf"^-\s*{re.escape(key)}:\s*(.+?)\s*$", text, re.M)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value


def numbered_count(value: str) -> int:
    return len(re.findall(r"^\d+\.\s+", value, re.M))


def validate_task(
    text: str, task_path: str, errors: list[str]
) -> tuple[str | None, dict[str, str | None]]:
    missing = sorted(TASK_HEADINGS - headings(text))
    if missing:
        errors.append(f"Task Spec missing durable headings: {', '.join(missing)}")
    task_headings = headings(text)
    forbidden = sorted(
        heading for heading in task_headings
        if any(heading.startswith(prefix) for prefix in TASK_FORBIDDEN_HEADINGS)
    )
    if forbidden:
        errors.append(f"Task Spec contains execution/review headings: {', '.join(forbidden)}")
    if VENDOR_BINDING.search(text):
        errors.append("Task Spec binds an executor role to a vendor/model")
    task_id = re.search(r"^#\s+(TASK-[A-Za-z0-9_-]+)\b", text, re.M)
    if not task_id:
        errors.append("Task Spec title must start with TASK-...")
        return None, {}
    for key in ("status", "priority", "difficulty", "dependencies", "current_attempt"):
        if field(text, key) is None:
            errors.append(f"Task Spec missing metadata field: {key}")
    resolved_id = task_id.group(1)
    if Path(task_path).name != f"{resolved_id}.md":
        errors.append("Task Spec filename does not match task ID")
    facts = {key: field(text, key) for key in ("priority", "difficulty")}
    return resolved_id, facts


def validate_capsule(
    text: str, task_id: str | None, task_facts: dict[str, str | None],
    task_path: str, capsule_path: str, errors: list[str], warnings: list[str]
) -> tuple[str | None, str | None]:
    missing = sorted(CAPSULE_HEADINGS - headings(text))
    if missing:
        errors.append(f"Capsule missing headings: {', '.join(missing)}")
    values = {key: field(text, key) for key in (
        "planning_source", "task_id", "attempt", "revision_reason", "priority",
        "difficulty", "required_planning_lookup"
    )}
    for key, value in values.items():
        if value is None:
            errors.append(f"Capsule missing metadata field: {key}")
    if values["planning_source"] and values["planning_source"].strip("`") != task_path:
        errors.append("Capsule planning_source does not match --task")
    if task_id and values["task_id"] != task_id:
        errors.append("Capsule task_id does not match Task Spec")
    if values["priority"] and task_facts.get("priority") != values["priority"]:
        errors.append("Capsule priority does not match Task Spec")
    if values["difficulty"] and task_facts.get("difficulty") != values["difficulty"]:
        errors.append("Capsule difficulty does not match Task Spec")
    if values["task_id"] and values["attempt"]:
        capsule_file = Path(capsule_path)
        if capsule_file.name != f"attempt-{values['attempt']}.md" or capsule_file.parent.name != values["task_id"]:
            errors.append("Capsule path does not match task_id and attempt metadata")
    lookup = values["required_planning_lookup"] or ""
    if lookup != "none" and ".md" in lookup and "#" not in lookup:
        errors.append("required_planning_lookup must name an exact heading, not a whole file")
    anchors = numbered_count(section(text, "源码锚点（最多 5 个）"))
    checks = numbered_count(section(text, "定向验证（最多 5 条）"))
    if not 1 <= anchors <= 5:
        errors.append(f"Capsule must contain 1–5 source anchors; found {anchors}")
    if not 1 <= checks <= 5:
        errors.append(f"Capsule must contain 1–5 targeted verification commands; found {checks}")
    allow = section(text, "修改白名单")
    max_files_match = re.search(r"max_modified_files:\s*`?(\d+)`?", allow)
    allowed_paths = [line for line in allow.splitlines() if re.match(r"^-\s+`[^`]+`\s*$", line)]
    if not max_files_match:
        errors.append("Capsule missing numeric max_modified_files")
    elif len(allowed_paths) > int(max_files_match.group(1)):
        errors.append("Capsule allowlist exceeds max_modified_files")
    if not allowed_paths:
        errors.append("Capsule file allowlist is empty")
    if not section(text, "已知基线失败"):
        errors.append("Capsule must state confirmed baseline failures or `none confirmed`")
    required_sections = (
        "本轮唯一目标", "已确认事实（禁止重新推导）", "源码锚点（最多 5 个）",
        "修改白名单", "定向验证（最多 5 条）", "已知基线失败", "停止条件"
    )
    unresolved = [name for name in required_sections if "待确认" in section(text, name)]
    if unresolved:
        errors.append(
            "Dispatch capsule contains unresolved facts: " + ", ".join(unresolved)
        )
    report = section(text, "精简 Implementation Report（固定格式）")
    for key in (
        "outcome", "changed_files", "anchors_touched", "verification",
        "active_findings", "scope_or_baseline_notes"
    ):
        if not re.search(rf"^-\s*{re.escape(key)}:", report, re.M):
            errors.append(f"Capsule Implementation Report missing field: {key}")
    if values["revision_reason"] == "changes_requested":
        active = section(text, "Active findings")
        if not re.search(r"F-[A-Za-z0-9_-]+", active) or re.search(r"\bnone\b", active, re.I):
            errors.append("Delta capsule must contain only explicit unresolved finding IDs")
    if VENDOR_BINDING.search(text):
        errors.append("Capsule binds an executor role to a vendor/model")
    if len(text) > 8000:
        warnings.append("Capsule is unusually long; split the Task or reduce projected context")
    return values["attempt"], values["revision_reason"]


def validate_review(
    text: str, repo: Path, review_path: str, task_id: str | None,
    attempt: str | None, capsule_path: str, errors: list[str]
) -> None:
    missing = sorted(REVIEW_HEADINGS - headings(text))
    if missing:
        errors.append(f"Review Record missing headings: {', '.join(missing)}")
    for key in ("task_id", "attempt", "capsule", "reviewed_at", "verdict", "reviewer_role"):
        if field(text, key) is None:
            errors.append(f"Review Record missing metadata field: {key}")
    if task_id and field(text, "task_id") != task_id:
        errors.append("Review Record task_id does not match Task Spec")
    if attempt and field(text, "attempt") != attempt:
        errors.append("Review Record attempt does not match Capsule")
    if field(text, "capsule") != capsule_path:
        errors.append("Review Record capsule path does not match --capsule")
    review_task = field(text, "task_id")
    review_attempt = field(text, "attempt")
    if review_task and review_attempt:
        record_file = Path(review_path)
        if record_file.name != f"attempt-{review_attempt}.md" or record_file.parent.name != review_task:
            errors.append("Review Record path does not match task_id and attempt metadata")
    verdict = field(text, "verdict")
    reviewer_role = field(text, "reviewer_role")
    if verdict not in ALLOWED_VERDICTS:
        errors.append(f"Review Record has invalid verdict: {verdict}")
    if reviewer_role not in ALLOWED_REVIEWER_ROLES:
        errors.append(f"Review Record has invalid reviewer_role: {reviewer_role}")

    task_status = field(text, "task_status")
    next_capsule = field(text, "next_capsule")
    active_next = field(text, "active_findings_for_next_attempt")
    for key, value in (
        ("task_status", task_status), ("next_capsule", next_capsule),
        ("active_findings_for_next_attempt", active_next)
    ):
        if value is None:
            errors.append(f"Review Record missing next-state field: {key}")
    finding_section = section(text, "Findings")
    active_finding_ids = set(
        re.findall(r"(F-[A-Za-z0-9_-]+).*?\bactive\b", finding_section, re.I)
    )
    next_ids = set(re.findall(r"F-[A-Za-z0-9_-]+", active_next or ""))
    next_is_none = (active_next or "").strip().lower() == "none"

    if verdict in {"PASSED", "PASSED_WITH_NOTES"}:
        if task_status != "PASSED":
            errors.append("Passed review must set task_status to PASSED")
        if next_capsule != "none":
            errors.append("Passed review must not point to a next capsule")
        if not next_is_none or active_finding_ids:
            errors.append("Passed review must not retain active findings")
        evidence = section(text, "验证证据")
        if not re.search(r"\bPASS\b", evidence):
            errors.append("Passed review must contain PASS verification evidence")
    elif verdict == "CHANGES_REQUESTED":
        if task_status != "READY_FOR_CORRECTION":
            errors.append("CHANGES_REQUESTED must set task_status to READY_FOR_CORRECTION")
        if not active_finding_ids:
            errors.append("CHANGES_REQUESTED requires at least one active finding")
        if not next_ids or next_ids != active_finding_ids:
            errors.append("Next-attempt finding IDs must match active review findings")
        if not next_capsule or next_capsule == "none":
            errors.append("CHANGES_REQUESTED must point to the next attempt capsule")
        elif review_task and review_attempt and review_attempt.isdigit():
            expected_attempt = f"{int(review_attempt) + 1:02d}"
            expected_path = str(
                Path(capsule_path).parent / f"attempt-{expected_attempt}.md"
            )
            if next_capsule != expected_path:
                errors.append("next_capsule does not point to the next attempt")
            else:
                next_path, next_error = resolve(repo, next_capsule, "Next Capsule")
                if next_error:
                    errors.append(next_error)
                elif next_path:
                    next_text = next_path.read_text(encoding="utf-8")
                    if field(next_text, "task_id") != review_task:
                        errors.append("Next Capsule task_id does not match Review Record")
                    if field(next_text, "attempt") != expected_attempt:
                        errors.append("Next Capsule attempt metadata is not the next attempt")
                    if field(next_text, "revision_reason") != "changes_requested":
                        errors.append("Next Capsule must be a changes_requested delta")
                    capsule_findings = set(
                        re.findall(r"F-[A-Za-z0-9_-]+", section(next_text, "Active findings"))
                    )
                    if capsule_findings != active_finding_ids:
                        errors.append("Next Capsule findings do not match active review findings")
    elif verdict == "BLOCKED":
        if task_status != "BLOCKED":
            errors.append("BLOCKED review must set task_status to BLOCKED")
        if next_capsule != "none" or not next_is_none:
            errors.append("BLOCKED review must not dispatch a next capsule or active findings")
    if VENDOR_BINDING.search(text):
        errors.append("Review Record binds an executor role to a vendor/model")


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if not repo.is_dir():
        errors.append(f"invalid repository: {repo}")
    task, task_error = resolve(repo, args.task, "Task Spec")
    if task_error:
        errors.append(task_error)
    if args.mode in {"dispatch", "review"} and not args.capsule:
        errors.append(f"{args.mode} mode requires --capsule")
    if args.mode == "review" and not args.review:
        errors.append("review mode requires --review")
    if args.mode == "legacy" and (args.capsule or args.review):
        errors.append("legacy mode validates only the existing Task Spec")

    task_id: str | None = None
    task_facts: dict[str, str | None] = {}
    if task and args.mode != "legacy":
        task_id, task_facts = validate_task(
            task.read_text(encoding="utf-8"), args.task, errors
        )

    attempt: str | None = None
    capsule: Path | None = None
    if args.capsule:
        capsule, capsule_error = resolve(repo, args.capsule, "Capsule")
        if capsule_error:
            errors.append(capsule_error)
        elif args.mode != "legacy":
            attempt, _ = validate_capsule(
                capsule.read_text(encoding="utf-8"), task_id, task_facts,
                args.task, args.capsule, errors, warnings
            )

    if args.review:
        review, review_error = resolve(repo, args.review, "Review Record")
        if review_error:
            errors.append(review_error)
        elif args.mode != "legacy":
            validate_review(
                review.read_text(encoding="utf-8"), repo, args.review,
                task_id, attempt, args.capsule or "", errors
            )

    result = {
        "status": "PASS" if not errors else "FAIL",
        "mode": args.mode,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
