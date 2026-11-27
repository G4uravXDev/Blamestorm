import re
from dataclasses import dataclass
from typing import List, Optional
from .runner import run_git, GitResult
from .diff import parse_diff_output, FileDiff


@dataclass
class StashEntry:
    index: int
    selector: str  # e.g. stash@{0}
    branch: str
    message: str
    relative_date: str = ""


def get_stashes(cwd: Optional[str] = None) -> List[StashEntry]:
    """List all stashes."""
    res = run_git(["stash", "list", "--format=%gd|%cr|%gs"], cwd=cwd)
    if not res.success or not res.stdout:
        return []

    stashes: List[StashEntry] = []
    pattern = re.compile(r"stash@\{(\d+)\}")

    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) >= 3:
            selector = parts[0].strip()
            date_str = parts[1].strip()
            subject = parts[2].strip()

            idx_match = pattern.search(selector)
            idx = int(idx_match.group(1)) if idx_match else len(stashes)

            # Subject often format: "WIP on branch: hash message" or "On branch: message"
            branch = "unknown"
            if " on " in subject:
                branch_part = subject.split(" on ", 1)[1]
                branch = branch_part.split(":", 1)[0].strip()

            stashes.append(StashEntry(
                index=idx,
                selector=selector,
                branch=branch,
                message=subject,
                relative_date=date_str
            ))

    return stashes


def stash_save(message: Optional[str] = None, include_untracked: bool = False, keep_index: bool = False, cwd: Optional[str] = None) -> GitResult:
    """Save changes to a new stash."""
    cmd = ["stash", "push"]
    if include_untracked:
        cmd.append("-u")
    if keep_index:
        cmd.append("--keep-index")
    if message and message.strip():
        cmd.extend(["-m", message.strip()])
    return run_git(cmd, cwd=cwd)


def stash_pop(index: int = 0, cwd: Optional[str] = None) -> GitResult:
    """Pop a stash by index."""
    return run_git(["stash", "pop", f"stash@{{{index}}}"], cwd=cwd)


def stash_apply(index: int = 0, cwd: Optional[str] = None) -> GitResult:
    """Apply a stash without removing it."""
    return run_git(["stash", "apply", f"stash@{{{index}}}"], cwd=cwd)


def stash_drop(index: int = 0, cwd: Optional[str] = None) -> GitResult:
    """Drop a stash."""
    return run_git(["stash", "drop", f"stash@{{{index}}}"], cwd=cwd)


def stash_clear(cwd: Optional[str] = None) -> GitResult:
    """Drop all stashes."""
    return run_git(["stash", "clear"], cwd=cwd)


def get_stash_diff(index: int = 0, cwd: Optional[str] = None) -> List[FileDiff]:
    """Get the diff for a specific stash."""
    res = run_git(["stash", "show", "-p", f"stash@{{{index}}}"], cwd=cwd)
    return parse_diff_output(res.stdout) if res.success else []
