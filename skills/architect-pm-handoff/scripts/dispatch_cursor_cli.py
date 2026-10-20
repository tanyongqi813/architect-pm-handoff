#!/usr/bin/env python3
"""Dispatch one Cursor CLI capsule with bounded macOS Extension Host recovery."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time


DEFAULT_IDLE_SECONDS = 12 * 60
HEALTH_TIMEOUT_SECONDS = 90


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Absolute repository root")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--capsule", help="Repository-relative Execution Capsule path")
    source.add_argument("--task", help="Legacy repository-relative Task Spec path")
    parser.add_argument("--idle-seconds", type=int, default=DEFAULT_IDLE_SECONDS)
    parser.add_argument("--agent-command", help="Explicit Cursor CLI executable")
    parser.add_argument("--model", help="Optional Cursor model name")
    parser.add_argument(
        "--allow-recovery",
        action="store_true",
        help="Allow one Extension Host restart and at most one fresh retry",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def resolve_inputs(args: argparse.Namespace) -> tuple[Path, Path, bool]:
    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        raise ValueError(f"Repository does not exist: {repo}")
    if not repo.is_absolute():
        raise ValueError("Repository path must be absolute")

    source_value = args.capsule or args.task
    assert source_value is not None
    source_arg = Path(source_value)
    if source_arg.is_absolute():
        raise ValueError("Capsule/Task path must be relative to the repository")
    source_path = (repo / source_arg).resolve()
    try:
        source_path.relative_to(repo)
    except ValueError as exc:
        raise ValueError("Capsule/Task path escapes the repository") from exc
    if not source_path.is_file():
        raise ValueError(f"Capsule/Task file does not exist: {source_path}")
    if args.idle_seconds < 60:
        raise ValueError("Idle timeout must be at least 60 seconds")

    return repo, source_path, args.capsule is None


def resolve_agent(requested: str | None) -> str:
    agent = requested or shutil.which("agent") or shutil.which("cursor-agent")
    if not agent:
        raise ValueError("Cursor CLI not found (expected agent or cursor-agent)")
    return agent


def metadata_field(text: str, key: str) -> str | None:
    match = re.search(rf"^-\s*{re.escape(key)}:\s*(.+?)\s*$", text, re.M)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value


def validate_capsule_before_dispatch(repo: Path, capsule: Path) -> None:
    text = capsule.read_text(encoding="utf-8")
    planning_source = metadata_field(text, "planning_source")
    if not planning_source:
        raise ValueError("Capsule validation failed: missing planning_source")
    task_arg = Path(planning_source)
    if task_arg.is_absolute():
        raise ValueError("Capsule validation failed: planning_source must be repository-relative")
    task = (repo / task_arg).resolve()
    try:
        task.relative_to(repo)
    except ValueError as exc:
        raise ValueError("Capsule validation failed: planning_source escapes repository") from exc
    if not task.is_file():
        raise ValueError(f"Capsule validation failed: Task Spec does not exist: {planning_source}")

    validator = Path(__file__).resolve().parent / "validate_handoff_artifacts.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(validator),
            "--repo",
            str(repo),
            "--mode",
            "dispatch",
            "--task",
            task_arg.as_posix(),
            "--capsule",
            capsule.relative_to(repo).as_posix(),
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        return
    reasons: list[str] = []
    try:
        result = json.loads(completed.stdout)
        reasons = [str(item) for item in result.get("errors", [])]
    except json.JSONDecodeError:
        pass
    detail = "; ".join(reasons[:5]) or completed.stderr.strip() or "unknown validator error"
    raise ValueError(f"Capsule validation failed: {detail}")


def git_status(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.stdout


def build_command(
    agent: str, source_path: Path, repo: Path, model: str | None, legacy: bool
) -> list[str]:
    relative_source = source_path.relative_to(repo).as_posix()
    if legacy:
        prompt = (
            f"执行旧版任务说明 @{relative_source}；只完成该任务，不推导缺失的文件范围、"
            "验证命令或基线；遇到缺失事实立即停止并报告。完成后输出精简 Implementation Report。"
        )
    else:
        prompt = (
            f"执行 @{relative_source}；只读取胶囊列出的源码锚点，只修改白名单文件，"
            "只运行定向验证，并按胶囊固定格式返回精简 Implementation Report。"
        )
    command = [
        agent,
        "-p",
        "--force",
        "--output-format",
        "stream-json",
        "--stream-partial-output",
    ]
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    return command


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def run_once(command: list[str], repo: Path, idle_seconds: int, log_path: Path) -> tuple[str, int]:
    process = subprocess.Popen(
        command,
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        start_new_session=True,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    last_event = time.monotonic()

    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n$ {shlex.join(command)}\n")
        while True:
            events = selector.select(timeout=1.0)
            for key, _ in events:
                line = key.fileobj.readline()
                if line:
                    last_event = time.monotonic()
                    rendered = line if key.data == "stdout" else f"[stderr] {line}"
                    sys.stdout.write(rendered)
                    sys.stdout.flush()
                    log.write(rendered)
                    log.flush()
                else:
                    selector.unregister(key.fileobj)

            if process.poll() is not None and not selector.get_map():
                return "completed", process.returncode
            if time.monotonic() - last_event >= idle_seconds:
                log.write(f"\n[watchdog] no CLI event for {idle_seconds} seconds\n")
                log.flush()
                stop_process(process)
                return "stalled", 124


def restart_extension_host(script_dir: Path) -> None:
    script = script_dir / "restart_cursor_extension_host.sh"
    subprocess.run(["zsh", str(script)], check=True)


def health_check(agent: str, repo: Path) -> bool:
    command = [
        agent,
        "-p",
        "--mode",
        "ask",
        "--output-format",
        "text",
        "Reply exactly READY. Do not inspect or modify files and do not run commands.",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=HEALTH_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False
    return completed.returncode == 0 and "READY" in completed.stdout


def main() -> int:
    args = parse_args()
    try:
        repo, source_path, legacy = resolve_inputs(args)
        if not legacy:
            validate_capsule_before_dispatch(repo, source_path)
        agent = resolve_agent(args.agent_command)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    command = build_command(agent, source_path, repo, args.model, legacy)
    if args.dry_run:
        print(f"cwd: {repo}")
        print(shlex.join(command))
        print(f"idle timeout: {args.idle_seconds}s")
        print(f"automatic recovery: {args.allow_recovery}")
        return 0

    baseline = git_status(repo)
    with tempfile.NamedTemporaryFile(
        prefix=f"cursor-{source_path.stem}-", suffix=".log", delete=False
    ) as handle:
        log_path = Path(handle.name)
    print(f"Cursor CLI log: {log_path}")

    state, code = run_once(command, repo, args.idle_seconds, log_path)
    if state == "completed":
        return code
    if not args.allow_recovery:
        print("Cursor CLI stalled; automatic recovery was not authorized.", file=sys.stderr)
        return 124

    current = git_status(repo)
    try:
        restart_extension_host(Path(__file__).resolve().parent)
    except subprocess.CalledProcessError as exc:
        print(f"Extension Host restart failed: {exc}", file=sys.stderr)
        return 70
    if not health_check(agent, repo):
        print("Cursor CLI health check failed after recovery.", file=sys.stderr)
        return 70
    if current != baseline:
        print(
            "Extension Host recovered, but the stalled attempt changed the workspace; "
            "automatic retry was skipped for lead-AI review.",
            file=sys.stderr,
        )
        return 75

    print("Extension Host recovered; retrying once in a fresh Cursor CLI session.")
    retry_state, retry_code = run_once(command, repo, args.idle_seconds, log_path)
    if retry_state == "stalled":
        print("The single retry also stalled; no further restart will be attempted.", file=sys.stderr)
        return 76
    return retry_code


if __name__ == "__main__":
    raise SystemExit(main())
