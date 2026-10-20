#!/usr/bin/env python3
"""Commit and push only explicitly approved Task-scoped paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
}
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


def run(
    args: list[str], repo: Path, *, check: bool = True, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=repo,
        text=True,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Absolute Git repository path")
    parser.add_argument("--task-id", required=True, help="Task identifier, e.g. TASK-020")
    parser.add_argument("--title", required=True, help="Short Task title")
    parser.add_argument("--spec", required=True, help="Repository-relative Task Spec path")
    parser.add_argument("--capsule", required=True, help="Repository-relative Execution Capsule")
    parser.add_argument("--review", required=True, help="Repository-relative Review Record")
    parser.add_argument("--verdict", choices=["PASSED", "PASSED_WITH_NOTES"], required=True)
    parser.add_argument("--priority", choices=["P0", "P1", "P2", "P3"], required=True)
    parser.add_argument("--difficulty", choices=["Low", "Medium", "High"], required=True)
    parser.add_argument("--path", action="append", required=True, dest="paths")
    parser.add_argument("--verification", action="append", required=True)
    parser.add_argument("--push", action="store_true", help="Push to the existing upstream")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def fail(message: str, code: int = 2) -> int:
    print(f"error: {message}", file=sys.stderr)
    return code


def normalize_relative(repo: Path, value: str) -> str:
    raw = Path(value)
    if raw.is_absolute():
        raise ValueError(f"path must be repository-relative: {value}")
    resolved = (repo / raw).resolve()
    try:
        relative = resolved.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {value}") from exc
    return relative.as_posix()


def is_sensitive(path: str) -> bool:
    item = Path(path)
    lower_parts = {part.lower() for part in item.parts}
    return (
        item.name.lower() in SENSITIVE_NAMES
        or item.suffix.lower() in SENSITIVE_SUFFIXES
        or "secrets" in lower_parts
    )


def git_state_in_progress(repo: Path) -> str | None:
    for label, git_path in (
        ("merge", "MERGE_HEAD"),
        ("rebase", "rebase-merge"),
        ("rebase", "rebase-apply"),
        ("cherry-pick", "CHERRY_PICK_HEAD"),
        ("revert", "REVERT_HEAD"),
    ):
        path = run(["git", "rev-parse", "--git-path", git_path], repo).stdout.strip()
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = repo / candidate
        if candidate.exists():
            return label
    return None


def nul_paths(output: str) -> list[str]:
    return [item for item in output.split("\0") if item]


def metadata_field(text: str, key: str) -> str | None:
    match = re.search(rf"^-\s*{re.escape(key)}:\s*(.+?)\s*$", text, re.M)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value


def validate_review_bundle(
    repo: Path, spec: str, capsule: str, review: str
) -> list[str]:
    validator = Path(__file__).resolve().parent / "validate_handoff_artifacts.py"
    completed = run(
        [
            sys.executable,
            str(validator),
            "--repo",
            str(repo),
            "--mode",
            "review",
            "--task",
            spec,
            "--capsule",
            capsule,
            "--review",
            review,
        ],
        repo,
        check=False,
    )
    if completed.returncode == 0:
        return []
    try:
        result = json.loads(completed.stdout)
        return [str(item) for item in result.get("errors", [])] or ["unknown validator error"]
    except json.JSONDecodeError:
        return [completed.stderr.strip() or "invalid validator output"]


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_absolute() or not repo.is_dir():
        return fail(f"invalid repository: {repo}")
    if run(["git", "rev-parse", "--is-inside-work-tree"], repo, check=False).stdout.strip() != "true":
        return fail(f"not a Git work tree: {repo}")

    branch = run(["git", "branch", "--show-current"], repo).stdout.strip()
    if not branch:
        return fail("detached HEAD is not eligible for automatic sync")
    in_progress = git_state_in_progress(repo)
    if in_progress:
        return fail(f"Git {in_progress} is in progress")

    try:
        paths = sorted({normalize_relative(repo, value) for value in args.paths})
        spec = normalize_relative(repo, args.spec)
        capsule = normalize_relative(repo, args.capsule)
        review = normalize_relative(repo, args.review)
    except ValueError as exc:
        return fail(str(exc))
    required_artifacts = {spec, capsule, review}
    missing_artifacts = sorted(required_artifacts - set(paths))
    if missing_artifacts:
        return fail(
            "approved paths must include Task Spec, Capsule, and Review Record: "
            + ", ".join(missing_artifacts)
        )
    sensitive = [path for path in paths if is_sensitive(path)]
    if sensitive:
        return fail(f"sensitive-looking paths require manual handling: {', '.join(sensitive)}")

    bundle_errors = validate_review_bundle(repo, spec, capsule, review)
    if bundle_errors:
        return fail("review bundle validation failed: " + "; ".join(bundle_errors[:5]))

    spec_text = (repo / spec).read_text(encoding="utf-8")
    capsule_text = (repo / capsule).read_text(encoding="utf-8")
    review_text = (repo / review).read_text(encoding="utf-8")
    task_match = re.search(r"^#\s+(TASK-[A-Za-z0-9_-]+)\b", spec_text, re.M)
    document_task_id = task_match.group(1) if task_match else None
    if document_task_id != args.task_id:
        return fail("--task-id does not match Task Spec")
    for key, supplied in (("priority", args.priority), ("difficulty", args.difficulty)):
        task_value = metadata_field(spec_text, key)
        capsule_value = metadata_field(capsule_text, key)
        if task_value != supplied or capsule_value != supplied:
            return fail(f"--{key} does not match Task Spec and Capsule")
    review_verdict = metadata_field(review_text, "verdict")
    if review_verdict != args.verdict:
        return fail("--verdict does not match Review Record")
    evidence = re.search(
        r"^##\s+验证证据\s*$\n(.*?)(?=^##\s+|\Z)", review_text, re.M | re.S
    )
    if not evidence or not re.search(r"\bPASS\b", evidence.group(1)):
        return fail("Review Record has no passing acceptance verification evidence")
    invalid_verification = [
        item for item in args.verification
        if not item.strip()
        or not re.search(r"\bPASS\b", item)
        or re.search(r"\b(?:FAIL|NOT_RUN)\b", item)
    ]
    if invalid_verification:
        return fail("every --verification must record a passing command/check")

    pre_staged = nul_paths(
        run(["git", "diff", "--cached", "--name-only", "-z"], repo).stdout
    )
    outside = sorted(set(pre_staged) - set(paths))
    if outside:
        return fail(f"unrelated paths are already staged: {', '.join(outside)}")

    upstream = run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        repo,
        check=False,
    ).stdout.strip()
    if args.push and not upstream:
        return fail("current branch has no upstream; automatic push is disabled")

    if args.dry_run:
        print(
            json.dumps(
                {
                    "repo": str(repo),
                    "branch": branch,
                    "upstream": upstream or None,
                    "task": args.task_id,
                    "capsule": capsule,
                    "review": review,
                    "paths": paths,
                    "would_push": args.push,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    run(["git", "add", "-A", "--", *paths], repo)
    staged = nul_paths(run(["git", "diff", "--cached", "--name-only", "-z"], repo).stdout)
    outside = sorted(set(staged) - set(paths))
    if outside:
        return fail(f"staging escaped approved paths: {', '.join(outside)}")
    if not staged:
        return fail("no approved changes to commit")
    if run(["git", "diff", "--cached", "--check"], repo, check=False).returncode != 0:
        return fail("staged diff failed git diff --cached --check")

    safe_title = " ".join(args.title.split())[:60]
    if not safe_title:
        return fail("Task title must contain non-whitespace characters")
    subject = f"task({args.task_id}): {safe_title}"
    body_lines = [
        f"Task: {args.task_id}",
        f"Spec: {spec}",
        f"Capsule: {capsule}",
        f"Review record: {review}",
        f"Review: {args.verdict}",
        f"Priority: {args.priority}",
        f"Difficulty: {args.difficulty}",
        "Verification:",
        *[f"- {item}" for item in args.verification],
        "Changed paths:",
        *[f"- {item}" for item in staged],
    ]
    message = subject + "\n\n" + "\n".join(body_lines) + "\n"
    run(["git", "commit", "-F", "-"], repo, input_text=message)
    commit = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

    pushed = False
    if args.push:
        pushed_result = run(["git", "push"], repo, check=False)
        if pushed_result.returncode != 0:
            print(pushed_result.stderr, file=sys.stderr)
            print(
                json.dumps(
                    {
                        "commit": commit,
                        "branch": branch,
                        "upstream": upstream,
                        "pushed": False,
                        "paths": staged,
                    },
                    ensure_ascii=False,
                )
            )
            return 3
        pushed = True

    print(
        json.dumps(
            {
                "commit": commit,
                "branch": branch,
                "upstream": upstream or None,
                "pushed": pushed,
                "paths": staged,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
