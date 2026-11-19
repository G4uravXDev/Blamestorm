import os
import subprocess
import shutil
from dataclasses import dataclass
from typing import List, Optional

GIT_TIMEOUT = 30  # seconds


@dataclass
class GitResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    command: List[str]


class GitError(Exception):
    def __init__(self, message: str, result: Optional[GitResult] = None):
        super().__init__(message)
        self.result = result


def get_git_executable() -> str:
    """Find the git binary."""
    exe = shutil.which("git")
    if not exe:
        raise GitError("git executable not found in system PATH.")
    return exe


def run_git(args: List[str], cwd: Optional[str] = None, timeout: int = GIT_TIMEOUT) -> GitResult:
    """
    Execute a git command with timeout and return GitResult.
    Does not raise an exception on non-zero exit code.
    """
    git_bin = get_git_executable()
    cmd = [git_bin] + [str(a) for a in args]
    
    # If cwd is provided, check if it exists
    working_dir = None
    if cwd and os.path.isdir(cwd):
        working_dir = os.path.abspath(cwd)

    try:
        proc = subprocess.run(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False,
            encoding="utf-8",
            errors="replace"
        )
        return GitResult(
            success=(proc.returncode == 0),
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            returncode=proc.returncode,
            command=cmd
        )
    except subprocess.TimeoutExpired:
        return GitResult(
            success=False,
            stdout="",
            stderr=f"Command '{' '.join(cmd)}' timed out after {timeout} seconds.",
            returncode=-1,
            command=cmd
        )
    except Exception as e:
        return GitResult(
            success=False,
            stdout="",
            stderr=f"Execution error: {str(e)}",
            returncode=-2,
            command=cmd
        )


def run_git_ok(args: List[str], cwd: Optional[str] = None, timeout: int = GIT_TIMEOUT) -> str:
    """
    Run git command and return stdout if success, otherwise raise GitError.
    """
    result = run_git(args, cwd=cwd, timeout=timeout)
    if not result.success:
        err_msg = result.stderr or f"Git command failed with exit code {result.returncode}"
        raise GitError(f"git {' '.join(args)} failed: {err_msg}", result=result)
    return result.stdout


def get_repo_root(cwd: Optional[str] = None) -> Optional[str]:
    """Get the toplevel directory of the git repo."""
    res = run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    if res.success and res.stdout:
        return os.path.normpath(res.stdout)
    return None


def is_git_repo(path: Optional[str] = None) -> bool:
    """Check if the given path is within a valid git working tree."""
    res = run_git(["rev-parse", "--is-inside-work-tree"], cwd=path)
    return res.success and res.stdout.strip() == "true"


def init_repo(path: str) -> GitResult:
    """Initialize a new git repository in the specified directory."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return run_git(["init"], cwd=path)
