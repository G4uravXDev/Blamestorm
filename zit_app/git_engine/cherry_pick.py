from typing import List, Optional
from .runner import run_git, GitResult
from .log import CommitEntry


def get_cherry_pick_candidates(from_branch: str, max_count: int = 30, cwd: Optional[str] = None) -> List[CommitEntry]:
    """
    Get commits present on `from_branch` that are not yet on current HEAD (`git log HEAD..from_branch`).
    """
    fmt = "%H|%h|%an|%ae|%ar|%s"
    cmd = ["log", f"--format={fmt}", f"-n{max_count}", f"HEAD..{from_branch}"]
    res = run_git(cmd, cwd=cwd)
    if not res.success or not res.stdout:
        return []

    commits: List[CommitEntry] = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) >= 6:
            commits.append(CommitEntry(
                hash=parts[0].strip(),
                short_hash=parts[1].strip(),
                author_name=parts[2].strip(),
                author_email=parts[3].strip(),
                relative_date=parts[4].strip(),
                subject=parts[5].strip()
            ))

    return commits


def cherry_pick(commit_hash: str, no_commit: bool = False, cwd: Optional[str] = None) -> GitResult:
    """Apply the changes introduced by a commit to the current branch."""
    cmd = ["cherry-pick"]
    if no_commit:
        cmd.append("-n")
    cmd.append(commit_hash)
    return run_git(cmd, cwd=cwd)


def cherry_pick_continue(cwd: Optional[str] = None) -> GitResult:
    """Continue an in-progress cherry-pick after resolving conflicts."""
    return run_git(["cherry-pick", "--continue"], cwd=cwd)


def cherry_pick_abort(cwd: Optional[str] = None) -> GitResult:
    """Cancel the cherry-pick operation and return to pre-cherry-pick state."""
    return run_git(["cherry-pick", "--abort"], cwd=cwd)
