import os
from dataclasses import dataclass, field
from typing import List, Optional
from .runner import run_git, GitResult, get_repo_root


@dataclass
class ConflictRegion:
    start_line: int
    end_line: int
    current: List[str]
    incoming: List[str]
    ancestor: Optional[List[str]] = None
    current_label: str = "HEAD"
    incoming_label: str = "Incoming"

    @property
    def current_text(self) -> str:
        return "\n".join(self.current)

    @property
    def incoming_text(self) -> str:
        return "\n".join(self.incoming)


@dataclass
class ConflictFile:
    path: str
    raw_content: str
    regions: List[ConflictRegion] = field(default_factory=list)
    total_lines: int = 0


@dataclass
class MergeState:
    is_merging: bool = False
    merge_type: str = "none"  # "merge", "rebase", "cherry-pick"
    head_name: str = "HEAD"
    merge_head: Optional[str] = None


def get_merge_state(cwd: Optional[str] = None) -> MergeState:
    """Detect if a merge, rebase, or cherry-pick operation is in progress."""
    root = get_repo_root(cwd)
    if not root:
        return MergeState()

    git_dir = os.path.join(root, ".git")
    if not os.path.exists(git_dir):
        # Worktree or submodule: check rev-parse --git-dir
        res = run_git(["rev-parse", "--git-dir"], cwd=cwd)
        if res.success and res.stdout:
            git_dir = os.path.abspath(res.stdout)
        else:
            return MergeState()

    head_name = "HEAD"
    head_res = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if head_res.success:
        head_name = head_res.stdout.strip()

    merge_head_path = os.path.join(git_dir, "MERGE_HEAD")
    if os.path.exists(merge_head_path):
        try:
            with open(merge_head_path, "r", encoding="utf-8", errors="replace") as f:
                mhead = f.read().strip()
        except Exception:
            mhead = None
        return MergeState(
            is_merging=True,
            merge_type="merge",
            head_name=head_name,
            merge_head=mhead
        )

    if os.path.exists(os.path.join(git_dir, "rebase-merge")) or os.path.exists(os.path.join(git_dir, "rebase-apply")):
        return MergeState(
            is_merging=True,
            merge_type="rebase",
            head_name=head_name
        )

    cp_path = os.path.join(git_dir, "CHERRY_PICK_HEAD")
    if os.path.exists(cp_path):
        try:
            with open(cp_path, "r", encoding="utf-8", errors="replace") as f:
                cp_head = f.read().strip()
        except Exception:
            cp_head = None
        return MergeState(
            is_merging=True,
            merge_type="cherry-pick",
            head_name=head_name,
            merge_head=cp_head
        )

    return MergeState()


def get_conflicted_files(cwd: Optional[str] = None) -> List[str]:
    """List files currently marked as unmerged/conflicted."""
    res = run_git(["diff", "--name-only", "--diff-filter=U"], cwd=cwd)
    if not res.success or not res.stdout:
        return []
    return [l.strip() for l in res.stdout.splitlines() if l.strip()]


def parse_conflict_markers(content: str) -> List[ConflictRegion]:
    """Parse conflict markers inside a file into ConflictRegion objects."""
    regions: List[ConflictRegion] = []
    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("<<<<<<<"):
            start_line = i + 1
            current_label = line.replace("<<<<<<<", "").strip() or "HEAD"
            current: List[str] = []
            ancestor: Optional[List[str]] = None
            incoming: List[str] = []
            incoming_label = "Incoming"

            i += 1
            # Current lines
            while i < len(lines) and not lines[i].startswith("=======") and not lines[i].startswith("|||||||"):
                current.append(lines[i])
                i += 1

            # Check for diff3 ancestor
            if i < len(lines) and lines[i].startswith("|||||||"):
                ancestor = []
                i += 1
                while i < len(lines) and not lines[i].startswith("======="):
                    ancestor.append(lines[i])
                    i += 1

            # Divider
            if i < len(lines) and lines[i].startswith("======="):
                i += 1

            # Incoming lines
            while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                incoming.append(lines[i])
                i += 1

            end_line = i + 1
            if i < len(lines) and lines[i].startswith(">>>>>>>"):
                incoming_label = lines[i].replace(">>>>>>>", "").strip() or "Incoming"

            regions.append(ConflictRegion(
                start_line=start_line,
                end_line=end_line,
                current=current,
                incoming=incoming,
                ancestor=ancestor,
                current_label=current_label,
                incoming_label=incoming_label
            ))

        i += 1

    return regions


def get_conflict_file(file_path: str, cwd: Optional[str] = None) -> Optional[ConflictFile]:
    """Read conflicted file and parse conflict regions."""
    root = get_repo_root(cwd) or cwd or "."
    full_path = os.path.join(root, file_path)
    if not os.path.exists(full_path):
        return None

    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return None

    regions = parse_conflict_markers(content)
    total_lines = len(content.splitlines())
    return ConflictFile(
        path=file_path,
        raw_content=content,
        regions=regions,
        total_lines=total_lines
    )


def resolve_ours(file_path: str, cwd: Optional[str] = None) -> GitResult:
    """Resolve conflict by checking out current (ours) version and staging."""
    checkout_res = run_git(["checkout", "--ours", "--", file_path], cwd=cwd)
    if not checkout_res.success:
        return checkout_res
    return run_git(["add", "--", file_path], cwd=cwd)


def resolve_theirs(file_path: str, cwd: Optional[str] = None) -> GitResult:
    """Resolve conflict by checking out incoming (theirs) version and staging."""
    checkout_res = run_git(["checkout", "--theirs", "--", file_path], cwd=cwd)
    if not checkout_res.success:
        return checkout_res
    return run_git(["add", "--", file_path], cwd=cwd)


def resolve_both(file_path: str, keep_order: str = "current_first", cwd: Optional[str] = None) -> GitResult:
    """Resolve conflict by keeping both current and incoming content, then staging."""
    root = get_repo_root(cwd) or cwd or "."
    full_path = os.path.join(root, file_path)
    if not os.path.exists(full_path):
        return GitResult(False, "", f"File {file_path} not found", 1, [])

    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        lines = content.splitlines()
        new_lines: List[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("<<<<<<<"):
                current: List[str] = []
                incoming: List[str] = []
                i += 1
                while i < len(lines) and not lines[i].startswith("=======") and not lines[i].startswith("|||||||"):
                    current.append(lines[i])
                    i += 1
                if i < len(lines) and lines[i].startswith("|||||||"):
                    while i < len(lines) and not lines[i].startswith("======="):
                        i += 1
                if i < len(lines) and lines[i].startswith("======="):
                    i += 1
                while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                    incoming.append(lines[i])
                    i += 1
                if i < len(lines) and lines[i].startswith(">>>>>>>"):
                    i += 1

                if keep_order == "current_first":
                    new_lines.extend(current)
                    new_lines.extend(incoming)
                else:
                    new_lines.extend(incoming)
                    new_lines.extend(current)
                continue

            new_lines.append(line)
            i += 1

        with open(full_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")

        return run_git(["add", "--", file_path], cwd=cwd)
    except Exception as e:
        return GitResult(False, "", str(e), 1, [])


def resolve_custom(file_path: str, resolved_content: str, cwd: Optional[str] = None) -> GitResult:
    """Save custom resolved content (e.g. from Gemini AI) and stage the file."""
    root = get_repo_root(cwd) or cwd or "."
    full_path = os.path.join(root, file_path)
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(resolved_content)
        return run_git(["add", "--", file_path], cwd=cwd)
    except Exception as e:
        return GitResult(False, "", str(e), 1, [])


def abort_merge(cwd: Optional[str] = None) -> GitResult:
    """Abort an active merge, rebase, or cherry-pick."""
    state = get_merge_state(cwd)
    if state.merge_type == "rebase":
        return run_git(["rebase", "--abort"], cwd=cwd)
    elif state.merge_type == "cherry-pick":
        return run_git(["cherry-pick", "--abort"], cwd=cwd)
    return run_git(["merge", "--abort"], cwd=cwd)


def continue_merge(message: Optional[str] = None, cwd: Optional[str] = None) -> GitResult:
    """Commit/continue the active merge or rebase."""
    state = get_merge_state(cwd)
    if state.merge_type == "rebase":
        return run_git(["rebase", "--continue"], cwd=cwd)
    elif state.merge_type == "cherry-pick":
        return run_git(["cherry-pick", "--continue"], cwd=cwd)
    
    cmd = ["commit"]
    if message:
        cmd.extend(["-m", message])
    return run_git(cmd, cwd=cwd)
