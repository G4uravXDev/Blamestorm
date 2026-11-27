from dataclasses import dataclass
from typing import List, Optional
from .runner import run_git, GitResult


@dataclass
class RemoteInfo:
    name: str
    fetch_url: str = ""
    push_url: str = ""


def get_remotes(cwd: Optional[str] = None) -> List[RemoteInfo]:
    """List configured remotes with their URLs."""
    res = run_git(["remote", "-v"], cwd=cwd)
    if not res.success or not res.stdout:
        return []

    remotes_dict = {}
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            name = parts[0]
            url = parts[1]
            typ = parts[2].strip("()")
            if name not in remotes_dict:
                remotes_dict[name] = RemoteInfo(name=name)
            if typ == "fetch":
                remotes_dict[name].fetch_url = url
            elif typ == "push":
                remotes_dict[name].push_url = url

    return list(remotes_dict.values())


def add_remote(name: str, url: str, cwd: Optional[str] = None) -> GitResult:
    """Add a new git remote."""
    return run_git(["remote", "add", name, url], cwd=cwd)


def remove_remote(name: str, cwd: Optional[str] = None) -> GitResult:
    """Remove a git remote."""
    return run_git(["remote", "remove", name], cwd=cwd)


def fetch_remote(remote: str = "origin", prune: bool = True, cwd: Optional[str] = None) -> GitResult:
    """Fetch updates from remote."""
    cmd = ["fetch", remote]
    if prune:
        cmd.append("--prune")
    return run_git(cmd, cwd=cwd)


def pull(remote: str = "origin", branch: Optional[str] = None, rebase: bool = False, cwd: Optional[str] = None) -> GitResult:
    """Pull updates from remote."""
    cmd = ["pull"]
    if rebase:
        cmd.append("--rebase")
    cmd.append(remote)
    if branch:
        cmd.append(branch)
    return run_git(cmd, cwd=cwd)


def push(
    remote: str = "origin",
    branch: Optional[str] = None,
    set_upstream: bool = False,
    force: bool = False,
    force_with_lease: bool = False,
    cwd: Optional[str] = None
) -> GitResult:
    """Push commits to remote."""
    cmd = ["push"]
    if set_upstream:
        cmd.append("-u")
    if force_with_lease:
        cmd.append("--force-with-lease")
    elif force:
        cmd.append("--force")
    cmd.append(remote)
    if branch:
        cmd.append(branch)
    return run_git(cmd, cwd=cwd)


def sync(remote: str = "origin", branch: Optional[str] = None, cwd: Optional[str] = None) -> GitResult:
    """Fetch/pull then push."""
    pull_res = pull(remote=remote, branch=branch, cwd=cwd)
    if not pull_res.success:
        return pull_res
    return push(remote=remote, branch=branch, cwd=cwd)
