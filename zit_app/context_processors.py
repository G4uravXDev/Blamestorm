import os
from .git_engine.runner import get_repo_root, is_git_repo
from .git_engine.status import get_status


def zit_context(request):
    """Context processor providing repository and app status to all templates."""
    # Find active repo path from session or default
    session_repo = request.session.get("current_repo_path")
    
    if session_repo and os.path.exists(session_repo) and is_git_repo(session_repo):
        active_repo = session_repo
    else:
        # Check current working directory
        cwd = os.getcwd()
        if is_git_repo(cwd):
            active_repo = get_repo_root(cwd) or cwd
        else:
            active_repo = cwd
        request.session["current_repo_path"] = active_repo

    repo_is_valid = is_git_repo(active_repo)
    repo_status = get_status(active_repo) if repo_is_valid else None

    # Check AI key
    gemini_key = request.session.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    return {
        "app_name": "Blamestorm",
        "current_repo_path": active_repo,
        "repo_is_valid": repo_is_valid,
        "repo_status": repo_status,
        "gemini_configured": bool(gemini_key),
        "version": "v1.0.0 (Django Edition)",
        "zit_version": "v1.0.0 (Django Edition)",
    }
