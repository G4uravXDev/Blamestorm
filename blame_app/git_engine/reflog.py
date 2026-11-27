from dataclasses import dataclass
from typing import List, Optional
from .runner import run_git, GitResult


@dataclass
class ReflogEntry:
    index: int
    selector: str  # e.g. HEAD@{0}
    commit_hash: str
    action: str
    relative_time: str
    message: str


def get_reflog(max_count: int = 50, cwd: Optional[str] = None) -> List[ReflogEntry]:
    """Parse git reflog entries."""
    fmt = "%gD|%h|%gs|%cr"
    res = run_git(["reflog", f"--format={fmt}", f"-n{max_count}"], cwd=cwd)
    if not res.success or not res.stdout:
        return []

    entries: List[ReflogEntry] = []
    for idx, line in enumerate(res.stdout.splitlines()):
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) >= 4:
            selector = parts[0].strip()
            h = parts[1].strip()
            msg = parts[2].strip()
            time_str = parts[3].strip()

            # Extract action (e.g., commit, checkout, reset, pull, merge)
            action = msg.split(":")[0].strip() if ":" in msg else "action"

            entries.append(ReflogEntry(
                index=idx,
                selector=selector,
                commit_hash=h,
                action=action,
                relative_time=time_str,
                message=msg
            ))

    return entries


def checkout_reflog(selector: str, cwd: Optional[str] = None) -> GitResult:
    """Checkout a commit referenced in the reflog."""
    return run_git(["checkout", selector], cwd=cwd)


def reset_to_reflog(selector: str, mode: str = "mixed", cwd: Optional[str] = None) -> GitResult:
    """Reset to a commit from reflog (soft, mixed, or hard)."""
    flag = f"--{mode}" if mode in ("soft", "mixed", "hard") else "--mixed"
    return run_git(["reset", flag, selector], cwd=cwd)
