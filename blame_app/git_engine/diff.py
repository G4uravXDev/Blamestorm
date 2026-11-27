import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional
from .runner import run_git, run_git_ok, GitResult, GitError


@dataclass
class DiffLine:
    line_type: str  # 'context', 'added', 'removed', 'header'
    content: str
    old_lineno: Optional[int] = None
    new_lineno: Optional[int] = None


@dataclass
class Hunk:
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[DiffLine] = field(default_factory=list)
    hunk_index: int = 0
    raw: str = ""


@dataclass
class FileDiff:
    path: str
    old_path: Optional[str] = None
    hunks: List[Hunk] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    raw: str = ""
    is_binary: bool = False


def parse_diff_output(diff_text: str) -> List[FileDiff]:
    """Parse raw git diff output into structured FileDiff objects."""
    if not diff_text or not diff_text.strip():
        return []

    file_diffs: List[FileDiff] = []
    current_file: Optional[FileDiff] = None
    current_hunk: Optional[Hunk] = None
    hunk_idx = 0

    old_lineno = 0
    new_lineno = 0

    hunk_header_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            # Flush previous hunk and file
            if current_hunk and current_file:
                current_file.hunks.append(current_hunk)
                current_hunk = None
            if current_file:
                file_diffs.append(current_file)

            # Match files in 'diff --git a/path b/path'
            parts = line.split(" ")
            path_b = parts[-1].lstrip("b/") if len(parts) >= 4 else "unknown"
            path_a = parts[-2].lstrip("a/") if len(parts) >= 4 else "unknown"

            current_file = FileDiff(
                path=path_b,
                old_path=path_a if path_a != path_b else None,
                raw=line + "\n"
            )
            hunk_idx = 0
            continue

        if current_file is None:
            continue

        current_file.raw += line + "\n"

        if "Binary files " in line:
            current_file.is_binary = True
            continue

        hunk_match = hunk_header_re.match(line)
        if hunk_match:
            if current_hunk:
                current_file.hunks.append(current_hunk)

            old_start = int(hunk_match.group(1))
            old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
            new_start = int(hunk_match.group(3))
            new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1

            old_lineno = old_start
            new_lineno = new_start

            current_hunk = Hunk(
                header=line,
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                hunk_index=hunk_idx,
                raw=line + "\n"
            )
            hunk_idx += 1
            continue

        if current_hunk is not None:
            current_hunk.raw += line + "\n"
            if line.startswith("+"):
                current_file.additions += 1
                current_hunk.lines.append(DiffLine(
                    line_type="added",
                    content=line,
                    new_lineno=new_lineno
                ))
                new_lineno += 1
            elif line.startswith("-"):
                current_file.deletions += 1
                current_hunk.lines.append(DiffLine(
                    line_type="removed",
                    content=line,
                    old_lineno=old_lineno
                ))
                old_lineno += 1
            elif line.startswith(" ") or line == "":
                current_hunk.lines.append(DiffLine(
                    line_type="context",
                    content=line,
                    old_lineno=old_lineno,
                    new_lineno=new_lineno
                ))
                old_lineno += 1
                new_lineno += 1
            elif line.startswith("\\"):
                current_hunk.lines.append(DiffLine(
                    line_type="header",
                    content=line
                ))

    if current_hunk and current_file:
        current_file.hunks.append(current_hunk)
    if current_file:
        file_diffs.append(current_file)

    return file_diffs


def get_unstaged_diff(cwd: Optional[str] = None, path: Optional[str] = None) -> List[FileDiff]:
    """Get diff of unstaged changes (working directory vs index)."""
    args = ["diff"]
    if path:
        args.extend(["--", path])
    res = run_git(args, cwd=cwd)
    return parse_diff_output(res.stdout) if res.success else []


def get_staged_diff(cwd: Optional[str] = None, path: Optional[str] = None) -> List[FileDiff]:
    """Get diff of staged changes (index vs HEAD)."""
    args = ["diff", "--cached"]
    if path:
        args.extend(["--", path])
    res = run_git(args, cwd=cwd)
    return parse_diff_output(res.stdout) if res.success else []


def get_raw_staged_diff(cwd: Optional[str] = None, path: Optional[str] = None) -> str:
    """Get raw text diff of staged changes."""
    args = ["diff", "--cached"]
    if path:
        args.extend(["--", path])
    res = run_git(args, cwd=cwd)
    return res.stdout if res.success else ""


def get_raw_unstaged_diff(cwd: Optional[str] = None, path: Optional[str] = None) -> str:
    """Get raw text diff of unstaged changes."""
    args = ["diff"]
    if path:
        args.extend(["--", path])
    res = run_git(args, cwd=cwd)
    return res.stdout if res.success else ""


def get_commit_diff(commit_hash: str, cwd: Optional[str] = None) -> List[FileDiff]:
    """Get diff for a specific commit."""
    res = run_git(["show", "--format=", commit_hash], cwd=cwd)
    return parse_diff_output(res.stdout) if res.success else []


def get_staged_stat(cwd: Optional[str] = None) -> str:
    """Get staged diffstat summary."""
    res = run_git(["diff", "--cached", "--stat"], cwd=cwd)
    return res.stdout if res.success else ""


def get_unstaged_stat(cwd: Optional[str] = None) -> str:
    """Get unstaged diffstat summary."""
    res = run_git(["diff", "--stat"], cwd=cwd)
    return res.stdout if res.success else ""


def stage_file(path: str, cwd: Optional[str] = None) -> GitResult:
    """Stage a single file or directory."""
    return run_git(["add", "--", path], cwd=cwd)


def unstage_file(path: str, cwd: Optional[str] = None) -> GitResult:
    """Unstage a single file."""
    # Check if file has a commit in HEAD
    check_head = run_git(["rev-parse", "HEAD"], cwd=cwd)
    if check_head.success:
        return run_git(["reset", "HEAD", "--", path], cwd=cwd)
    else:
        # First commit in repo
        return run_git(["rm", "--cached", "-r", "--", path], cwd=cwd)


def stage_all(cwd: Optional[str] = None) -> GitResult:
    """Stage all modified, deleted, and untracked files."""
    return run_git(["add", "-A"], cwd=cwd)


def unstage_all(cwd: Optional[str] = None) -> GitResult:
    """Unstage all files."""
    check_head = run_git(["rev-parse", "HEAD"], cwd=cwd)
    if check_head.success:
        return run_git(["reset", "HEAD"], cwd=cwd)
    else:
        return run_git(["rm", "--cached", "-r", "."], cwd=cwd)


def discard_file_changes(path: str, is_untracked: bool = False, cwd: Optional[str] = None) -> GitResult:
    """Discard uncommitted changes in a file or delete untracked file."""
    if is_untracked:
        # Untracked file: remove it
        full_path = os.path.join(cwd or ".", path)
        if os.path.isfile(full_path) or os.path.islink(full_path):
            try:
                os.remove(full_path)
                return GitResult(True, f"Removed {path}", "", 0, ["rm", path])
            except Exception as e:
                return GitResult(False, "", str(e), 1, ["rm", path])
        elif os.path.isdir(full_path):
            import shutil
            try:
                shutil.rmtree(full_path)
                return GitResult(True, f"Removed directory {path}", "", 0, ["rmdir", path])
            except Exception as e:
                return GitResult(False, "", str(e), 1, ["rmdir", path])
        return run_git(["clean", "-f", "--", path], cwd=cwd)
    else:
        # Modified file
        return run_git(["checkout", "HEAD", "--", path], cwd=cwd)


def build_hunk_patch(file_path: str, hunk: Hunk) -> str:
    """Construct a minimal patch string for a single hunk."""
    header = f"--- a/{file_path}\n+++ b/{file_path}\n{hunk.header}\n"
    lines = "\n".join(l.content for l in hunk.lines) + "\n"
    return header + lines


def stage_hunk(file_path: str, hunk: Hunk, cwd: Optional[str] = None) -> GitResult:
    """Stage a single hunk via `git apply --cached`."""
    patch = build_hunk_patch(file_path, hunk)
    try:
        proc = subprocess.run(
            ["git", "apply", "--cached", "--unidiff-zero"],
            input=patch,
            text=True,
            capture_output=True,
            cwd=cwd
        )
        return GitResult(
            success=(proc.returncode == 0),
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            returncode=proc.returncode,
            command=["git", "apply", "--cached"]
        )
    except Exception as e:
        return GitResult(False, "", str(e), 1, ["git", "apply", "--cached"])


def unstage_hunk(file_path: str, hunk: Hunk, cwd: Optional[str] = None) -> GitResult:
    """Unstage a single hunk via `git apply --cached -R`."""
    patch = build_hunk_patch(file_path, hunk)
    try:
        proc = subprocess.run(
            ["git", "apply", "--cached", "-R", "--unidiff-zero"],
            input=patch,
            text=True,
            capture_output=True,
            cwd=cwd
        )
        return GitResult(
            success=(proc.returncode == 0),
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            returncode=proc.returncode,
            command=["git", "apply", "--cached", "-R"]
        )
    except Exception as e:
        return GitResult(False, "", str(e), 1, ["git", "apply", "--cached", "-R"])
