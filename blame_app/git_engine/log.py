from dataclasses import dataclass, field
from typing import List, Optional
from .runner import run_git
from .diff import parse_diff_output, FileDiff


@dataclass
class CommitEntry:
    hash: str
    short_hash: str
    author_name: str
    author_email: str
    relative_date: str
    subject: str
    decorations: str = ""
    body: str = ""
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


@dataclass
class CommitDetail:
    commit: CommitEntry
    full_message: str
    diffstat: str
    diffs: List[FileDiff] = field(default_factory=list)


def get_commit_history(
    max_count: int = 50,
    branch: Optional[str] = None,
    search: Optional[str] = None,
    cwd: Optional[str] = None
) -> List[CommitEntry]:
    """
    Get commit log entries with structured fields.
    """
    fmt = "%H|%h|%an|%ae|%ar|%s|%D"
    cmd = ["log", f"--format={fmt}", f"-n{max_count}"]

    if search and search.strip():
        cmd.extend(["--grep", search.strip(), "-i"])

    if branch:
        cmd.append(branch)

    res = run_git(cmd, cwd=cwd)
    if not res.success or not res.stdout:
        return []

    commits: List[CommitEntry] = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) >= 6:
            full_hash = parts[0].strip()
            short_hash = parts[1].strip()
            author_name = parts[2].strip()
            author_email = parts[3].strip()
            rel_date = parts[4].strip()
            subject = parts[5].strip()
            decorations = parts[6].strip() if len(parts) > 6 else ""

            commits.append(CommitEntry(
                hash=full_hash,
                short_hash=short_hash,
                author_name=author_name,
                author_email=author_email,
                relative_date=rel_date,
                subject=subject,
                decorations=decorations
            ))

    return commits


def get_commit_graph(max_count: int = 30, cwd: Optional[str] = None) -> str:
    """Get ASCII commit graph via `git log --graph --oneline --decorate`."""
    res = run_git(["log", "--graph", "--oneline", "--decorate", f"-n{max_count}"], cwd=cwd)
    return res.stdout if res.success else ""


def get_commit_details(commit_hash: str, cwd: Optional[str] = None) -> Optional[CommitDetail]:
    """Get complete details and diffs for a specific commit."""
    # Read commit metadata
    fmt = "%H|%h|%an|%ae|%ar|%s|%B"
    meta_res = run_git(["show", "-s", f"--format={fmt}", commit_hash], cwd=cwd)
    if not meta_res.success:
        return None

    lines = meta_res.stdout.split("|", 6)
    if len(lines) < 7:
        return None

    full_hash, short_hash, aname, aemail, rdate, subj, body = (
        lines[0].strip(),
        lines[1].strip(),
        lines[2].strip(),
        lines[3].strip(),
        lines[4].strip(),
        lines[5].strip(),
        lines[6].strip(),
    )

    commit = CommitEntry(
        hash=full_hash,
        short_hash=short_hash,
        author_name=aname,
        author_email=aemail,
        relative_date=rdate,
        subject=subj,
        body=body
    )

    # Read diffstat
    stat_res = run_git(["show", "--stat", "--oneline", commit_hash], cwd=cwd)
    diffstat = stat_res.stdout if stat_res.success else ""

    # Read diffs
    diff_res = run_git(["show", "--format=", commit_hash], cwd=cwd)
    diffs = parse_diff_output(diff_res.stdout) if diff_res.success else []

    return CommitDetail(
        commit=commit,
        full_message=body or subj,
        diffstat=diffstat,
        diffs=diffs
    )
