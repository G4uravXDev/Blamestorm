import os
from .git_engine.runner import get_repo_root, is_git_repo
from .git_engine.status import get_status


def zit_context(request):
    """Context processor providing repository and app status to all templates."""
    # Find active repo path from session or environment
    env_repo = os.environ.get("ZIT_REPO_PATH")
    session_repo = request.session.get("current_repo_path")
    launched_repo = request.session.get("launched_repo")

    if env_repo and os.path.exists(env_repo) and launched_repo != env_repo:
        active_repo = env_repo
        request.session["launched_repo"] = env_repo
        request.session["current_repo_path"] = env_repo
    elif session_repo and os.path.exists(session_repo):
        active_repo = session_repo
    elif env_repo and os.path.exists(env_repo):
        active_repo = env_repo
        request.session["current_repo_path"] = env_repo
    else:
        cwd = os.getcwd()
        active_repo = get_repo_root(cwd) or cwd if is_git_repo(cwd) else cwd
        request.session["current_repo_path"] = active_repo

    repo_is_valid = is_git_repo(active_repo)
    repo_status = get_status(active_repo) if repo_is_valid else None

    # Check AI key & active model
    gemini_key = request.session.get("gemini_api_key")
    gemini_model = request.session.get("gemini_model")
    if not gemini_key or not gemini_model:
        try:
            from .models import ZitConfig
            config = ZitConfig.get_solo()
            if not gemini_key:
                gemini_key = config.gemini_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not gemini_model:
                gemini_model = config.gemini_model
        except Exception:
            pass

    gemini_model = gemini_model or "gemini-2.5-flash"

    return {
        "app_name": "Blamestorm",
        "current_repo_path": active_repo,
        "repo_is_valid": repo_is_valid,
        "repo_status": repo_status,
        "gemini_configured": bool(gemini_key),
        "gemini_model": gemini_model,
        "version": "v1.0.0 (Django Edition)",
        "zit_version": "v1.0.0 (Django Edition)",
    }
