from dataclasses import dataclass
from typing import List, Optional
from .runner import run_git, GitResult


@dataclass
class BranchInfo:
    name: str
    is_current: bool = False
    is_remote: bool = False
    upstream: Optional[str] = None
    commit_hash: str = ""
    subject: str = ""


def get_branches(cwd: Optional[str] = None) -> List[BranchInfo]:
    """
    List local and remote branches with upstream, HEAD indicator, commit, and subject.
    """
    res = run_git([
        "branch", "-a",
        "--format=%(refname:short)|%(upstream:short)|%(HEAD)|%(objectname:short)|%(subject)"
    ], cwd=cwd)

    if not res.success:
        return []

    branches: List[BranchInfo] = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) >= 5:
            refname = parts[0].strip()
            upstream = parts[1].strip() or None
            head_mark = parts[2].strip()
            objname = parts[3].strip()
            subject = parts[4].strip()

            is_current = (head_mark == "*")
            is_remote = refname.startswith("origin/") or "/" in refname and not refname.startswith("heads/")

            branches.append(BranchInfo(
                name=refname,
                is_current=is_current,
                is_remote=is_remote,
                upstream=upstream,
                commit_hash=objname,
                subject=subject
            ))

    return branches


def get_current_branch(cwd: Optional[str] = None) -> str:
    """Get the active branch name."""
    res = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if res.success:
        return res.stdout.strip()
    return "(unknown)"


def create_branch(name: str, start_point: Optional[str] = None, checkout: bool = True, cwd: Optional[str] = None) -> GitResult:
    """Create a new branch and optionally switch to it."""
    if checkout:
        cmd = ["checkout", "-b", name]
    else:
        cmd = ["branch", name]
    if start_point:
        cmd.append(start_point)
    return run_git(cmd, cwd=cwd)


def switch_branch(name: str, cwd: Optional[str] = None) -> GitResult:
    """Switch/checkout branch."""
    # Strip origin/ if user wants to checkout a remote branch locally
    target = name
    if name.startswith("origin/"):
        local_name = name[len("origin/"):]
        return run_git(["checkout", "--track", name], cwd=cwd)
    return run_git(["checkout", target], cwd=cwd)


def delete_branch(name: str, force: bool = False, is_remote: bool = False, cwd: Optional[str] = None) -> GitResult:
    """Delete a branch (safely with -d or forced with -D)."""
    if is_remote:
        # e.g. origin/feature -> push origin --delete feature
        parts = name.split("/", 1)
        remote = parts[0]
        remote_branch = parts[1] if len(parts) > 1 else name
        return run_git(["push", remote, "--delete", remote_branch], cwd=cwd)

    flag = "-D" if force else "-d"
    return run_git(["branch", flag, name], cwd=cwd)


def rename_branch(old_name: str, new_name: str, cwd: Optional[str] = None) -> GitResult:
    """Rename a branch."""
    return run_git(["branch", "-m", old_name, new_name], cwd=cwd)


def merge_branch(branch_name: str, no_ff: bool = False, squash: bool = False, message: Optional[str] = None, cwd: Optional[str] = None) -> GitResult:
    """Merge a branch into the current HEAD."""
    cmd = ["merge"]
    if no_ff:
        cmd.append("--no-ff")
    if squash:
        cmd.append("--squash")
    if message:
        cmd.extend(["-m", message])
    cmd.append(branch_name)
    return run_git(cmd, cwd=cwd)
