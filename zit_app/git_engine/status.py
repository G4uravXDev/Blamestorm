import re
from dataclasses import dataclass, field
from typing import List, Optional
from .runner import run_git, get_repo_root


@dataclass
class FileEntry:
    path: str
    status: str  # Modified, Added, Deleted, Renamed, Copied, Untracked, Conflicted
    status_code: str  # 'M', 'A', 'D', 'R', 'C', '?', 'U'
    original_path: Optional[str] = None


@dataclass
class RepoStatus:
    repo_path: str = ""
    branch: str = "(unknown)"
    upstream: Optional[str] = None
    ahead: int = 0
    behind: int = 0
    staged: List[FileEntry] = field(default_factory=list)
    unstaged: List[FileEntry] = field(default_factory=list)
    untracked: List[FileEntry] = field(default_factory=list)
    conflicts: List[FileEntry] = field(default_factory=list)
    stash_count: int = 0
    detached_head: bool = False

    @property
    def is_clean(self) -> bool:
        return (
            len(self.staged) == 0
            and len(self.unstaged) == 0
            and len(self.untracked) == 0
            and len(self.conflicts) == 0
        )

    @property
    def total_changed_files(self) -> int:
        return (
            len(self.staged)
            + len(self.unstaged)
            + len(self.untracked)
            + len(self.conflicts)
        )


def _char_to_status(c: str) -> str:
    mapping = {
        'M': "Modified",
        'A': "Added",
        'D': "Deleted",
        'R': "Renamed",
        'C': "Copied",
        'U': "Conflicted",
        '?': "Untracked",
        '!': "Ignored"
    }
    return mapping.get(c, "Modified")


def get_status(cwd: Optional[str] = None) -> RepoStatus:
    """
    Fetch repository status by parsing `git status --porcelain=v2 --branch`.
    """
    repo_root = get_repo_root(cwd) or cwd or ""
    res = run_git(["status", "--porcelain=v2", "--branch"], cwd=cwd)
    if not res.success:
        return RepoStatus(repo_path=repo_root, branch="(not a git repo)")

    branch = "(unknown)"
    upstream = None
    ahead = 0
    behind = 0
    staged: List[FileEntry] = []
    unstaged: List[FileEntry] = []
    untracked: List[FileEntry] = []
    conflicts: List[FileEntry] = []
    detached_head = False

    lines = res.stdout.splitlines()
    for line in lines:
        if line.startswith("# branch.head "):
            branch = line.replace("# branch.head ", "").strip()
            if branch == "(detached)":
                detached_head = True
        elif line.startswith("# branch.upstream "):
            upstream = line.replace("# branch.upstream ", "").strip()
        elif line.startswith("# branch.ab "):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    ahead = int(parts[2].lstrip("+"))
                except ValueError:
                    ahead = 0
                try:
                    behind = int(parts[3].lstrip("-"))
                except ValueError:
                    behind = 0
        elif line.startswith("1 "):
            # Format: 1 XY sub mH mI mW hH hI path
            parts = line.split(maxsplit=8)
            if len(parts) >= 9:
                xy = parts[1]
                path = parts[8].strip()
                x = xy[0] if len(xy) > 0 else '.'
                y = xy[1] if len(xy) > 1 else '.'

                if x not in ('.', '?'):
                    staged.append(FileEntry(path=path, status=_char_to_status(x), status_code=x))
                if y not in ('.', '?'):
                    unstaged.append(FileEntry(path=path, status=_char_to_status(y), status_code=y))

        elif line.startswith("2 "):
            # Format: 2 XY sub mH mI mW hH hI Xscore path\torigPath
            parts = line.split(maxsplit=9)
            if len(parts) >= 9:
                xy = parts[1]
                path_info = parts[-1].strip()
                if '\t' in path_info:
                    path, orig_path = path_info.split('\t', 1)
                else:
                    path, orig_path = path_info, None

                x = xy[0] if len(xy) > 0 else '.'
                y = xy[1] if len(xy) > 1 else '.'

                if x not in ('.', '?'):
                    staged.append(FileEntry(path=path, status=_char_to_status(x), status_code=x, original_path=orig_path))
                if y not in ('.', '?'):
                    unstaged.append(FileEntry(path=path, status=_char_to_status(y), status_code=y, original_path=orig_path))

        elif line.startswith("u "):
            # Unmerged/conflicted entry
            parts = line.split(maxsplit=10)
            if len(parts) >= 11:
                path = parts[10].strip()
                conflicts.append(FileEntry(path=path, status="Conflicted", status_code="U"))

        elif line.startswith("? "):
            path = line.replace("? ", "", 1).strip()
            untracked.append(FileEntry(path=path, status="Untracked", status_code="?"))

    # Stash count
    stash_res = run_git(["stash", "list"], cwd=cwd)
    stash_count = len(stash_res.stdout.splitlines()) if stash_res.success and stash_res.stdout else 0

    return RepoStatus(
        repo_path=repo_root,
        branch=branch,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        staged=staged,
        unstaged=unstaged,
        untracked=untracked,
        conflicts=conflicts,
        stash_count=stash_count,
        detached_head=detached_head
    )
