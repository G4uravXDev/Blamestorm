import os
import re
from dataclasses import dataclass
from typing import List, Optional
from .runner import run_git, GitResult, get_repo_root


@dataclass
class BisectStatus:
    active: bool = False
    phase: str = "inactive"  # "inactive", "in_progress", "found"
    current_commit: str = ""
    steps_remaining: int = 0
    revisions_left: int = 0
    first_bad_commit: str = ""
    summary: str = ""
    log_text: str = ""


def is_bisecting(cwd: Optional[str] = None) -> bool:
    """Check if git bisect is currently active."""
    root = get_repo_root(cwd)
    if not root:
        return False
    bisect_log = os.path.join(root, ".git", "BISECT_LOG")
    return os.path.exists(bisect_log)


def get_bisect_status(cwd: Optional[str] = None) -> BisectStatus:
    """Get the current state of git bisect."""
    if not is_bisecting(cwd):
        return BisectStatus(active=False, phase="inactive")

    log_res = run_git(["bisect", "log"], cwd=cwd)
    log_text = log_res.stdout if log_res.success else ""

    # Current commit being checked
    head_res = run_git(["rev-parse", "HEAD"], cwd=cwd)
    current_commit = head_res.stdout.strip() if head_res.success else ""

    status_res = run_git(["status"], cwd=cwd)
    status_text = status_res.stdout if status_res.success else ""

    steps_remaining = 0
    revisions_left = 0
    first_bad_commit = ""
    phase = "in_progress"
    summary = ""

    # Check if found
    for line in log_text.splitlines() + status_text.splitlines():
        if "is the first bad commit" in line:
            phase = "found"
            first_bad_commit = line.split()[0] if line.split() else ""
            summary = line
            break
        step_match = re.search(r"Roughly (\d+) steps?.*\(roughly (\d+) revisions?\)", line)
        if step_match:
            steps_remaining = int(step_match.group(1))
            revisions_left = int(step_match.group(2))

    return BisectStatus(
        active=True,
        phase=phase,
        current_commit=current_commit,
        steps_remaining=steps_remaining,
        revisions_left=revisions_left,
        first_bad_commit=first_bad_commit,
        summary=summary,
        log_text=log_text
    )


def bisect_start(bad: str = "HEAD", good: str = "HEAD~5", cwd: Optional[str] = None) -> GitResult:
    """Start a bisect session with bad and good revisions."""
    return run_git(["bisect", "start", bad, good], cwd=cwd)


def bisect_good(commit: Optional[str] = None, cwd: Optional[str] = None) -> GitResult:
    """Mark commit (or HEAD) as good."""
    cmd = ["bisect", "good"]
    if commit:
        cmd.append(commit)
    return run_git(cmd, cwd=cwd)


def bisect_bad(commit: Optional[str] = None, cwd: Optional[str] = None) -> GitResult:
    """Mark commit (or HEAD) as bad."""
    cmd = ["bisect", "bad"]
    if commit:
        cmd.append(commit)
    return run_git(cmd, cwd=cwd)


def bisect_skip(commit: Optional[str] = None, cwd: Optional[str] = None) -> GitResult:
    """Skip testing the current revision."""
    cmd = ["bisect", "skip"]
    if commit:
        cmd.append(commit)
    return run_git(cmd, cwd=cwd)


def bisect_reset(cwd: Optional[str] = None) -> GitResult:
    """Reset bisect session and return to original HEAD."""
    return run_git(["bisect", "reset"], cwd=cwd)
