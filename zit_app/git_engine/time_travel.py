from dataclasses import dataclass
from typing import List, Optional
from .runner import run_git, GitResult


@dataclass
class TagInfo:
    name: str
    commit_hash: str
    message: str = ""


def reset_soft(target: str = "HEAD~1", cwd: Optional[str] = None) -> GitResult:
    """Soft reset: Moves HEAD to target, leaves index and working directory intact."""
    return run_git(["reset", "--soft", target], cwd=cwd)


def reset_mixed(target: str = "HEAD~1", cwd: Optional[str] = None) -> GitResult:
    """Mixed reset: Moves HEAD and resets index, preserves working directory changes."""
    return run_git(["reset", "--mixed", target], cwd=cwd)


def reset_hard(target: str = "HEAD~1", cwd: Optional[str] = None) -> GitResult:
    """Hard reset: Resets index and working tree. Any changes since target are discarded."""
    return run_git(["reset", "--hard", target], cwd=cwd)


def restore_file(file_path: str, source: str = "HEAD", cwd: Optional[str] = None) -> GitResult:
    """Restore working tree file to a specific commit or HEAD."""
    return run_git(["checkout", source, "--", file_path], cwd=cwd)


def clean_untracked(cwd: Optional[str] = None) -> GitResult:
    """Remove untracked files and directories."""
    return run_git(["clean", "-fd"], cwd=cwd)


def get_tags(cwd: Optional[str] = None) -> List[TagInfo]:
    """List tags with commit hash and annotations."""
    res = run_git(["tag", "-l", "--format=%(refname:short)|%(objectname:short)|%(subject)"], cwd=cwd)
    if not res.success or not res.stdout:
        return []

    tags = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        name = parts[0].strip()
        h = parts[1].strip() if len(parts) > 1 else ""
        msg = parts[2].strip() if len(parts) > 2 else ""
        tags.append(TagInfo(name=name, commit_hash=h, message=msg))
    return tags


def create_tag(name: str, message: Optional[str] = None, commit_hash: Optional[str] = None, cwd: Optional[str] = None) -> GitResult:
    """Create a tag."""
    cmd = ["tag"]
    if message:
        cmd.extend(["-a", name, "-m", message])
    else:
        cmd.append(name)
    if commit_hash:
        cmd.append(commit_hash)
    return run_git(cmd, cwd=cwd)


def delete_tag(name: str, cwd: Optional[str] = None) -> GitResult:
    """Delete a tag."""
    return run_git(["tag", "-d", name], cwd=cwd)
