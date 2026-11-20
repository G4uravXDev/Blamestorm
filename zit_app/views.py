import os
import json
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

from .models import ZitConfig, WorkflowPreset, AgentMessage
from .git_engine.runner import run_git, get_repo_root, is_git_repo, init_repo
from .git_engine.status import get_status
from .git_engine.diff import (
    get_staged_diff, get_unstaged_diff, get_raw_staged_diff, get_raw_unstaged_diff,
    get_commit_diff, get_staged_stat, get_unstaged_stat, stage_file, unstage_file, stage_all,
    unstage_all, discard_file_changes, stage_hunk, unstage_hunk
)
from .git_engine.branch import (
    get_branches, get_current_branch, create_branch, switch_branch,
    delete_branch, rename_branch, merge_branch
)
from .git_engine.log import get_commit_history, get_commit_graph, get_commit_details
from .git_engine.time_travel import (
    reset_soft, reset_mixed, reset_hard, restore_file, clean_untracked,
    get_tags, create_tag, delete_tag
)
from .git_engine.reflog import get_reflog, checkout_reflog, reset_to_reflog
from .git_engine.stash import (
    get_stashes, stash_save, stash_pop, stash_apply, stash_drop, stash_clear, get_stash_diff
)
from .git_engine.merge import (
    get_merge_state, get_conflicted_files, get_conflict_file,
    resolve_ours, resolve_theirs, resolve_both, resolve_custom,
    abort_merge, continue_merge
)
from .git_engine.bisect import (
    get_bisect_status, bisect_start, bisect_good, bisect_bad, bisect_skip, bisect_reset
)
from .git_engine.cherry_pick import (
    get_cherry_pick_candidates, cherry_pick, cherry_pick_continue, cherry_pick_abort
)
from .git_engine.remote import get_remotes, add_remote, remove_remote, fetch_remote, pull, push, sync
from .git_engine.secrets import scan_diff_content, scan_file_content

from .ai_engine.gemini_client import get_ai_client, GeminiClient
from .ai_engine.agent_runner import run_agent_turn, classify_command_safety

logger = logging.getLogger(__name__)


def _get_active_repo(request):
    """Retrieve verified active repository path from session or default."""
    repo = request.session.get("current_repo_path")
    if not repo or not os.path.exists(repo):
        cwd = os.getcwd()
        if is_git_repo(cwd):
            repo = get_repo_root(cwd) or cwd
        else:
            repo = cwd
        request.session["current_repo_path"] = repo
    return repo


def dashboard_view(request):
    """Repository Dashboard view."""
    repo_path = _get_active_repo(request)
    is_valid = is_git_repo(repo_path)
    status = get_status(repo_path) if is_valid else None
    recent_commits = get_commit_history(max_count=8, cwd=repo_path) if is_valid else []
    remotes = get_remotes(repo_path) if is_valid else []
    merge_state = get_merge_state(repo_path) if is_valid else None

    context = {
        "active_view": "dashboard",
        "status": status,
        "recent_commits": recent_commits,
        "remotes": remotes,
        "merge_state": merge_state,
        "is_valid": is_valid,
    }
    return render(request, "zit/dashboard.html", context)


def staging_view(request):
    """Smart Staging view with unified diff and hunk actions."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    status = get_status(repo_path)
    selected_file = request.GET.get("file", "").strip()
    diff_type = request.GET.get("type", "unstaged").strip()  # staged or unstaged

    file_diffs = []
    # Only populate diffs if the user has explicitly selected a file
    if selected_file:
        if diff_type == "staged":
            file_diffs = get_staged_diff(repo_path, path=selected_file)
        else:
            file_diffs = get_unstaged_diff(repo_path, path=selected_file)

    # Secret scanning on staged files
    raw_staged = get_raw_staged_diff(repo_path)
    config = ZitConfig.get_solo()
    allowlist = [a.strip() for a in config.secrets_allowlist.splitlines() if a.strip()]
    secrets_found = scan_diff_content(raw_staged, allowlist=allowlist) if config.auto_scan_secrets else []

    context = {
        "active_view": "staging",
        "status": status,
        "selected_file": selected_file,
        "diff_type": diff_type,
        "file_diffs": file_diffs,
        "secrets_found": secrets_found,
    }
    return render(request, "zit/staging.html", context)


def commit_view(request):
    """Guided Commit editor view with conventional commit builder and Gemini suggestions."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    status = get_status(repo_path)
    staged_diffs = get_staged_diff(repo_path)
    diffstat = get_staged_stat(repo_path)
    raw_diff = get_raw_staged_diff(repo_path)

    config = ZitConfig.get_solo()
    allowlist = [a.strip() for a in config.secrets_allowlist.splitlines() if a.strip()]
    secrets_found = scan_diff_content(raw_diff, allowlist=allowlist) if config.auto_scan_secrets else []

    if request.method == "POST":
        commit_type = request.POST.get("commit_type", "").strip()
        scope = request.POST.get("scope", "").strip()
        subject = request.POST.get("subject", "").strip()
        body = request.POST.get("body", "").strip()
        is_breaking = request.POST.get("is_breaking") == "on"
        bypass_secrets = request.POST.get("bypass_secrets") == "on"

        if secrets_found and not bypass_secrets:
            messages.error(request, f"Blocked commit: {len(secrets_found)} secret(s) detected in staged changes! Resolve them or check 'Bypass secret warnings'.")
        elif not subject:
            messages.error(request, "Commit subject cannot be empty.")
        else:
            # Build conventional commit message
            prefix = commit_type
            if scope:
                prefix += f"({scope})"
            if is_breaking:
                prefix += "!"
            if prefix:
                full_subject = f"{prefix}: {subject}"
            else:
                full_subject = subject

            full_message = full_subject
            if body:
                full_message += f"\n\n{body}"
            if is_breaking:
                full_message += "\n\nBREAKING CHANGE: see commit details."

            res = run_git(["commit", "-m", full_message], cwd=repo_path)
            if res.success:
                messages.success(request, f"Committed successfully: {full_subject}")
                return redirect("zit:staging")
            else:
                messages.error(request, f"Commit failed: {res.stderr}")

    context = {
        "active_view": "commit",
        "status": status,
        "staged_diffs": staged_diffs,
        "diffstat": diffstat,
        "secrets_found": secrets_found,
    }
    return render(request, "zit/commit.html", context)


def branches_view(request):
    """Visual Branch manager view."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    branches = get_branches(repo_path)
    current_branch = get_current_branch(repo_path)

    context = {
        "active_view": "branches",
        "branches": branches,
        "current_branch": current_branch,
    }
    return render(request, "zit/branches.html", context)


def timeline_view(request):
    """Commit Timeline and visual graph view."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    search_query = request.GET.get("q", "").strip()
    selected_hash = request.GET.get("commit", "").strip()

    commits = get_commit_history(max_count=60, search=search_query or None, cwd=repo_path)
    graph_text = get_commit_graph(max_count=40, cwd=repo_path)

    commit_detail = None
    if selected_hash:
        commit_detail = get_commit_details(selected_hash, cwd=repo_path)
    elif commits:
        commit_detail = get_commit_details(commits[0].hash, cwd=repo_path)

    context = {
        "active_view": "timeline",
        "commits": commits,
        "graph_text": graph_text,
        "search_query": search_query,
        "commit_detail": commit_detail,
        "selected_hash": selected_hash,
    }
    return render(request, "zit/timeline.html", context)


def time_travel_view(request):
    """Safe Reset, Restore, and Tag management."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    recent_commits = get_commit_history(max_count=15, cwd=repo_path)
    tags = get_tags(repo_path)

    context = {
        "active_view": "time_travel",
        "recent_commits": recent_commits,
        "tags": tags,
    }
    return render(request, "zit/time_travel.html", context)


def reflog_view(request):
    """Reflog Recovery view."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    reflog_entries = get_reflog(max_count=60, cwd=repo_path)

    context = {
        "active_view": "reflog",
        "reflog_entries": reflog_entries,
    }
    return render(request, "zit/reflog.html", context)


def stash_view(request):
    """Stash manager view."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    stashes = get_stashes(repo_path)
    selected_idx = request.GET.get("idx")
    stash_diffs = []
    if selected_idx is not None:
        try:
            stash_diffs = get_stash_diff(int(selected_idx), cwd=repo_path)
        except ValueError:
            pass

    context = {
        "active_view": "stash",
        "stashes": stashes,
        "selected_idx": selected_idx,
        "stash_diffs": stash_diffs,
    }
    return render(request, "zit/stash.html", context)


def merge_resolve_view(request):
    """Merge conflict resolution view."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    merge_state = get_merge_state(repo_path)
    conflicted_files = get_conflicted_files(repo_path)
    selected_file = request.GET.get("file", "")

    if not selected_file and conflicted_files:
        selected_file = conflicted_files[0]

    conflict_data = None
    if selected_file:
        conflict_data = get_conflict_file(selected_file, cwd=repo_path)

    context = {
        "active_view": "merge_resolve",
        "merge_state": merge_state,
        "conflicted_files": conflicted_files,
        "selected_file": selected_file,
        "conflict_data": conflict_data,
    }
    return render(request, "zit/merge_resolve.html", context)


def bisect_view(request):
    """Interactive Git Bisect view."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    status = get_bisect_status(repo_path)
    recent_commits = get_commit_history(max_count=20, cwd=repo_path)

    context = {
        "active_view": "bisect",
        "bisect_status": status,
        "recent_commits": recent_commits,
    }
    return render(request, "zit/bisect.html", context)


def cherry_pick_view(request):
    """Cherry pick commits from other branches."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    branches = get_branches(repo_path)
    selected_branch = request.GET.get("branch", "")
    if not selected_branch and branches:
        other_branches = [b.name for b in branches if not b.is_current]
        selected_branch = other_branches[0] if other_branches else ""

    candidates = get_cherry_pick_candidates(selected_branch, cwd=repo_path) if selected_branch else []

    selected_hash = request.GET.get("commit", "")
    commit_diffs = []
    if selected_hash:
        commit_diffs = get_commit_diff(selected_hash, cwd=repo_path)

    context = {
        "active_view": "cherry_pick",
        "branches": branches,
        "selected_branch": selected_branch,
        "candidates": candidates,
        "selected_hash": selected_hash,
        "commit_diffs": commit_diffs,
    }
    return render(request, "zit/cherry_pick.html", context)


def workflow_builder_view(request):
    """Visual GitHub Actions CI/CD Workflow Builder & Git Ops recipes."""
    repo_path = _get_active_repo(request)
    presets = WorkflowPreset.objects.all()

    context = {
        "active_view": "workflow_builder",
        "presets": presets,
        "repo_path": repo_path,
    }
    return render(request, "zit/workflow_builder.html", context)


def github_view(request):
    """GitHub integration view (remotes, sync, pull requests)."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    remotes = get_remotes(repo_path)
    status = get_status(repo_path)

    context = {
        "active_view": "github",
        "remotes": remotes,
        "status": status,
    }
    return render(request, "zit/github.html", context)


def ai_mentor_view(request):
    """AI Mentor panel (explain, ask questions, recommendations, error diagnosis)."""
    repo_path = _get_active_repo(request)
    status = get_status(repo_path) if is_git_repo(repo_path) else None
    recent_commits = get_commit_history(max_count=5, cwd=repo_path) if is_git_repo(repo_path) else []

    context = {
        "active_view": "ai_mentor",
        "status": status,
        "recent_commits": recent_commits,
    }
    return render(request, "zit/ai_mentor.html", context)


def ai_code_studio_view(request):
    """3-Pane AI Mentor Code Studio: Current Code | AI Mentor Terminal | Suggested Code."""
    repo_path = _get_active_repo(request)
    if not is_git_repo(repo_path):
        return redirect("zit:dashboard")

    status = get_status(repo_path)
    file_path = request.GET.get("file", "").strip()
    diff_type = request.GET.get("type", "unstaged").strip()

    # Collect changed files for switcher dropdown
    changed_files = []
    if status:
        for f in status.staged:
            if f.path not in changed_files:
                changed_files.append(f.path)
        for f in status.unstaged:
            if f.path not in changed_files:
                changed_files.append(f.path)
        for f in status.untracked:
            if f.path not in changed_files:
                changed_files.append(f.path)

    # If no file specified, default to first changed file
    if not file_path and changed_files:
        file_path = changed_files[0]

    file_content = ""
    file_lines = []
    file_exists = False
    file_error = ""

    if file_path:
        full_path = os.path.abspath(os.path.join(repo_path, file_path))
        if full_path.startswith(os.path.abspath(repo_path)):
            if os.path.isfile(full_path):
                file_exists = True
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        file_content = f.read()
                    file_lines = file_content.splitlines()
                except Exception as e:
                    file_error = str(e)
            else:
                file_error = f"File '{file_path}' does not exist on disk."
        else:
            file_error = "Access denied: file path is outside active repository."

    context = {
        "active_view": "code_mentor",
        "status": status,
        "current_repo_path": repo_path,
        "file_path": file_path,
        "diff_type": diff_type,
        "changed_files": changed_files,
        "file_content": file_content,
        "file_lines": file_lines,
        "file_lines_count": len(file_lines),
        "file_exists": file_exists,
        "file_error": file_error,
    }
    return render(request, "zit/code_mentor.html", context)


def agent_view(request):
    """Autonomous AI Agent Mode view."""
    repo_path = _get_active_repo(request)
    messages_list = AgentMessage.objects.filter(session_id="default")

    context = {
        "active_view": "agent",
        "messages": messages_list,
        "repo_path": repo_path,
    }
    return render(request, "zit/agent.html", context)


STANDARD_GEMINI_MODELS = [
    ("gemini-2.5-flash", "gemini-2.5-flash (Fast, latest & recommended)"),
    ("gemini-2.0-flash", "gemini-2.0-flash (High speed)"),
    ("gemini-1.5-flash", "gemini-1.5-flash (Stable fast model)"),
    ("gemini-1.5-pro", "gemini-1.5-pro (High intelligence)"),
    ("gemini-2.0-flash-lite", "gemini-2.0-flash-lite (Lightweight, low latency)"),
]
STANDARD_MODEL_KEYS = [k for k, _ in STANDARD_GEMINI_MODELS]


def settings_view(request):
    """Application and Gemini API settings view."""
    config = ZitConfig.get_solo()
    repo_path = _get_active_repo(request)

    if request.method == "POST":
        gemini_key = request.POST.get("gemini_api_key", "").strip()
        gemini_model_choice = request.POST.get("gemini_model", "").strip()
        custom_model = request.POST.get("custom_gemini_model", "").strip()

        if gemini_model_choice == "custom":
            gemini_model = custom_model or "gemini-2.5-flash"
        else:
            gemini_model = gemini_model_choice or custom_model or "gemini-2.5-flash"

        confirm_dest = request.POST.get("confirm_destructive") == "on"
        auto_scan = request.POST.get("auto_scan_secrets") == "on"
        allowlist = request.POST.get("secrets_allowlist", "").strip()
        new_repo = request.POST.get("active_repo_path", "").strip()

        config.gemini_api_key = gemini_key
        config.gemini_model = gemini_model
        config.confirm_destructive = confirm_dest
        config.auto_scan_secrets = auto_scan
        config.secrets_allowlist = allowlist
        config.save()

        # Update session
        request.session["gemini_api_key"] = gemini_key
        request.session["gemini_model"] = gemini_model

        if new_repo and os.path.exists(new_repo):
            request.session["current_repo_path"] = os.path.abspath(new_repo)

        messages.success(request, f"Settings updated successfully (Model: {gemini_model}).")
        return redirect("zit:settings")

    is_custom_model = bool(config.gemini_model and config.gemini_model not in STANDARD_MODEL_KEYS)

    context = {
        "active_view": "settings",
        "config": config,
        "repo_path": repo_path,
        "standard_models": STANDARD_GEMINI_MODELS,
        "is_custom_model": is_custom_model,
    }
    return render(request, "zit/settings.html", context)


# ═══════════════════════════════════════════════════════════════
# JSON API ENDPOINTS (AJAX ACTIONS)
# ═══════════════════════════════════════════════════════════════

@csrf_exempt
def api_git_command(request):
    """Execute standard git commands via AJAX."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    repo_path = _get_active_repo(request)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    action = data.get("action", "")

    try:
        if action == "stage_file":
            res = stage_file(data["path"], cwd=repo_path)
        elif action == "unstage_file":
            res = unstage_file(data["path"], cwd=repo_path)
        elif action == "stage_all":
            res = stage_all(cwd=repo_path)
        elif action == "unstage_all":
            res = unstage_all(cwd=repo_path)
        elif action == "discard_file":
            is_untracked = data.get("is_untracked", False)
            res = discard_file_changes(data["path"], is_untracked=is_untracked, cwd=repo_path)
        elif action == "stage_hunk":
            from .git_engine.diff import Hunk, DiffLine
            hunk_data = data["hunk"]
            lines = [DiffLine(line_type=l.get("type", "context"), content=l.get("content", "")) for l in hunk_data.get("lines", [])]
            hunk = Hunk(
                header=hunk_data["header"],
                old_start=hunk_data["old_start"],
                old_count=hunk_data["old_count"],
                new_start=hunk_data["new_start"],
                new_count=hunk_data["new_count"],
                lines=lines
            )
            res = stage_hunk(data["path"], hunk, cwd=repo_path)
        elif action == "unstage_hunk":
            from .git_engine.diff import Hunk, DiffLine
            hunk_data = data["hunk"]
            lines = [DiffLine(line_type=l.get("type", "context"), content=l.get("content", "")) for l in hunk_data.get("lines", [])]
            hunk = Hunk(
                header=hunk_data["header"],
                old_start=hunk_data["old_start"],
                old_count=hunk_data["old_count"],
                new_start=hunk_data["new_start"],
                new_count=hunk_data["new_count"],
                lines=lines
            )
            res = unstage_hunk(data["path"], hunk, cwd=repo_path)
        elif action == "create_branch":
            res = create_branch(data["name"], start_point=data.get("start_point"), checkout=data.get("checkout", True), cwd=repo_path)
        elif action == "switch_branch":
            res = switch_branch(data["name"], cwd=repo_path)
        elif action == "delete_branch":
            res = delete_branch(data["name"], force=data.get("force", False), is_remote=data.get("is_remote", False), cwd=repo_path)
        elif action == "rename_branch":
            res = rename_branch(data["old_name"], data["new_name"], cwd=repo_path)
        elif action == "merge_branch":
            res = merge_branch(data["name"], no_ff=data.get("no_ff", False), squash=data.get("squash", False), cwd=repo_path)
        elif action == "reset_soft":
            res = reset_soft(data.get("target", "HEAD~1"), cwd=repo_path)
        elif action == "reset_mixed":
            res = reset_mixed(data.get("target", "HEAD~1"), cwd=repo_path)
        elif action == "reset_hard":
            res = reset_hard(data.get("target", "HEAD~1"), cwd=repo_path)
        elif action == "restore_file":
            res = restore_file(data["path"], source=data.get("source", "HEAD"), cwd=repo_path)
        elif action == "clean_untracked":
            res = clean_untracked(cwd=repo_path)
        elif action == "create_tag":
            res = create_tag(data["name"], message=data.get("message"), commit_hash=data.get("commit"), cwd=repo_path)
        elif action == "delete_tag":
            res = delete_tag(data["name"], cwd=repo_path)
        elif action == "checkout_reflog":
            res = checkout_reflog(data["selector"], cwd=repo_path)
        elif action == "reset_reflog":
            res = reset_to_reflog(data["selector"], mode=data.get("mode", "mixed"), cwd=repo_path)
        elif action == "stash_save":
            res = stash_save(message=data.get("message"), include_untracked=data.get("include_untracked", False), cwd=repo_path)
        elif action == "stash_pop":
            res = stash_pop(int(data.get("index", 0)), cwd=repo_path)
        elif action == "stash_apply":
            res = stash_apply(int(data.get("index", 0)), cwd=repo_path)
        elif action == "stash_drop":
            res = stash_drop(int(data.get("index", 0)), cwd=repo_path)
        elif action == "stash_clear":
            res = stash_clear(cwd=repo_path)
        elif action == "resolve_ours":
            res = resolve_ours(data["path"], cwd=repo_path)
        elif action == "resolve_theirs":
            res = resolve_theirs(data["path"], cwd=repo_path)
        elif action == "resolve_both":
            res = resolve_both(data["path"], keep_order=data.get("order", "current_first"), cwd=repo_path)
        elif action == "resolve_custom":
            res = resolve_custom(data["path"], data["content"], cwd=repo_path)
        elif action == "abort_merge":
            res = abort_merge(cwd=repo_path)
        elif action == "continue_merge":
            res = continue_merge(message=data.get("message"), cwd=repo_path)
        elif action == "bisect_start":
            res = bisect_start(bad=data.get("bad", "HEAD"), good=data.get("good", "HEAD~1"), cwd=repo_path)
        elif action == "bisect_good":
            res = bisect_good(commit=data.get("commit"), cwd=repo_path)
        elif action == "bisect_bad":
            res = bisect_bad(commit=data.get("commit"), cwd=repo_path)
        elif action == "bisect_skip":
            res = bisect_skip(commit=data.get("commit"), cwd=repo_path)
        elif action == "bisect_reset":
            res = bisect_reset(cwd=repo_path)
        elif action == "cherry_pick":
            res = cherry_pick(data["commit"], no_commit=data.get("no_commit", False), cwd=repo_path)
        elif action == "cherry_pick_continue":
            res = cherry_pick_continue(cwd=repo_path)
        elif action == "cherry_pick_abort":
            res = cherry_pick_abort(cwd=repo_path)
        elif action == "git_push":
            res = push(remote=data.get("remote", "origin"), branch=data.get("branch"), set_upstream=data.get("set_upstream", False), force=data.get("force", False), cwd=repo_path)
        elif action == "git_pull":
            res = pull(remote=data.get("remote", "origin"), branch=data.get("branch"), cwd=repo_path)
        elif action == "git_fetch":
            res = fetch_remote(remote=data.get("remote", "origin"), cwd=repo_path)
        elif action == "git_sync":
            res = sync(remote=data.get("remote", "origin"), branch=data.get("branch"), cwd=repo_path)
        elif action == "init_repo":
            res = init_repo(repo_path)
        else:
            return JsonResponse({"success": False, "error": f"Unknown action '{action}'"})

        return JsonResponse({
            "success": res.success,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "returncode": res.returncode
        })
    except Exception as e:
        logger.exception("Error executing git command")
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
def api_ai_commit(request):
    """Generate conventional commit suggestions from updated files diff using Gemini."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    repo_path = _get_active_repo(request)
    staged_diff = get_raw_staged_diff(repo_path)
    stat = get_staged_stat(repo_path)

    # If staged diff is empty, fall back to analyzing unstaged modified files
    if not staged_diff or not staged_diff.strip():
        staged_diff = get_raw_unstaged_diff(repo_path)
        stat = get_unstaged_stat(repo_path)

    ai_client = get_ai_client(request)
    try:
        suggestions = ai_client.generate_commit_suggestions(staged_diff, stat_summary=stat)
        return JsonResponse({"success": True, "suggestions": suggestions})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
def api_ai_mentor(request):
    """Run an AI Mentor query using Gemini."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    repo_path = _get_active_repo(request)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    query_type = data.get("query_type", "explain")
    user_question = data.get("question", "")
    extra_context = data.get("extra_context", "")

    status = get_status(repo_path) if is_git_repo(repo_path) else None
    recent = get_commit_history(max_count=5, cwd=repo_path) if is_git_repo(repo_path) else []

    if query_type == "review":
        extra_context += "\nStaged Diff:\n" + get_raw_staged_diff(repo_path)[:10000]

    ai_client = get_ai_client(request)
    try:
        answer = ai_client.mentor_query(
            query_type=query_type,
            repo_status=status,
            recent_commits=recent,
            user_message=user_question,
            extra_context=extra_context
        )
        return JsonResponse({"success": True, "answer": answer})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
def api_ai_code_mentor_query(request):
    """Run an interactive code mentor turn on a specific file."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    repo_path = _get_active_repo(request)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    file_path = data.get("file_path", "").strip()
    action = data.get("action", "custom").strip()
    user_instruction = data.get("prompt", "").strip()
    current_code = data.get("current_code", "")

    trimmed = user_instruction.strip()

    # 1. Clear command
    if trimmed.lower() in ("cls", "clear"):
        return JsonResponse({"success": True, "is_cmd": True, "clear": True})

    # 2. Help command
    if trimmed.lower() in ("help", "/help", "?"):
        help_text = (
            "Blamestorm CMD Terminal Commands:\n"
            "  git <command>      Run any git command (e.g. git status, git diff, git log -n 5)\n"
            "  dir / ls           List files in current repository directory\n"
            "  cls / clear        Clear terminal screen\n"
            "  explain            Analyze and explain the active file\n"
            "  review / bugs      Scan active file for bugs, edge cases, and vulnerabilities\n"
            "  refactor           Refactor and generate updated code in Right Box\n"
            "  docstrings         Add docstrings & type hints to active file\n"
            "  <any prompt>       Ask AI Mentor anything about this file or project"
        )
        return JsonResponse({"success": True, "is_cmd": True, "output": help_text})

    # 3. Direct git command execution in CMD terminal
    if trimmed.startswith("git ") or trimmed == "git":
        args = trimmed.split()[1:]
        res = run_git(args, cwd=repo_path)
        output = res.stdout if res.success else (res.stderr or res.stdout or "Command failed with no output.")
        return JsonResponse({"success": True, "is_cmd": True, "output": output})

    # 4. Directory listing
    if trimmed.lower() in ("dir", "ls"):
        try:
            files = sorted(os.listdir(repo_path))
            output = "\n".join(files)
        except Exception as e:
            output = str(e)
        return JsonResponse({"success": True, "is_cmd": True, "output": output})

    # 5. Quick action shortcuts typed directly into CMD
    if trimmed.lower() == "explain":
        action = "explain"
        user_instruction = ""
    elif trimmed.lower() in ("review", "bugs", "bug"):
        action = "review"
        user_instruction = ""
    elif trimmed.lower() in ("refactor", "optimize"):
        action = "refactor"
        user_instruction = ""
    elif trimmed.lower() in ("docstrings", "types", "docs"):
        action = "docstrings"
        user_instruction = ""

    # If current_code wasn't provided, read it from disk
    if not current_code and file_path:
        full_path = os.path.abspath(os.path.join(repo_path, file_path))
        if full_path.startswith(os.path.abspath(repo_path)) and os.path.isfile(full_path):
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    current_code = f.read()
            except Exception:
                pass

    if not user_instruction:
        if action == "explain":
            user_instruction = "Explain this file in detail. Describe its purpose, architecture, primary functions/classes, and key behavior."
        elif action == "review":
            user_instruction = "Review this file for potential bugs, logical issues, security vulnerabilities, and code quality improvements."
        elif action == "refactor":
            user_instruction = "Refactor and optimize this file for maximum readability, clean code architecture, performance, and best practices. Provide the complete updated code in ```UPDATED_CODE."
        elif action == "docstrings":
            user_instruction = "Add comprehensive type annotations and professional docstrings/comments to this file. Provide the complete updated code in ```UPDATED_CODE."
        else:
            user_instruction = "Explain what this file does and suggest any improvements."

    ai_client = get_ai_client(request)
    try:
        result = ai_client.mentor_code_turn(
            file_path=file_path,
            current_code=current_code,
            user_instruction=user_instruction,
            action=action
        )
        return JsonResponse({
            "success": True,
            "explanation": result["explanation"],
            "suggested_code": result["suggested_code"],
            "has_suggested_code": result["has_suggested_code"]
        })
    except Exception as e:
        logger.exception("AI Code Mentor query failed")
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
def api_ai_code_mentor_apply(request):
    """Apply suggested code directly to the file on disk."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    repo_path = _get_active_repo(request)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    file_path = data.get("file_path", "").strip()
    code = data.get("code", "")

    if not file_path:
        return JsonResponse({"success": False, "error": "No file path specified."})

    full_path = os.path.abspath(os.path.join(repo_path, file_path))
    if not full_path.startswith(os.path.abspath(repo_path)):
        return JsonResponse({"success": False, "error": "Security error: path outside active repo."})

    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)

        lines_count = len(code.splitlines())
        return JsonResponse({
            "success": True,
            "message": f"Successfully updated '{file_path}' ({lines_count} lines written).",
            "lines_count": lines_count,
            "new_code": code
        })
    except Exception as e:
        logger.exception("Failed to write updated code to file")
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
def api_ai_resolve(request):
    """Generate Gemini AI resolution for merge conflict."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    repo_path = _get_active_repo(request)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    file_path = data.get("path", "")
    conflict_file = get_conflict_file(file_path, cwd=repo_path)
    if not conflict_file:
        return JsonResponse({"success": False, "error": f"Conflict file '{file_path}' not found."})

    ai_client = get_ai_client(request)
    try:
        solution = ai_client.resolve_conflict(file_path, conflict_file.raw_content[:8000])
        return JsonResponse({"success": True, "resolution": solution})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
def api_agent_turn(request):
    """Autonomous Git Agent turn execution."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    repo_path = _get_active_repo(request)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    user_intent = data.get("intent", "").strip()
    session_id = data.get("session_id", "default")
    auto_execute = data.get("auto_execute", True)

    # Save user message
    if user_intent:
        AgentMessage.objects.create(session_id=session_id, role="user", content=user_intent)

    # Load history
    history_records = AgentMessage.objects.filter(session_id=session_id).order_by("timestamp")
    conv_history = [{"role": m.role, "content": m.content} for m in history_records]

    ai_client = get_ai_client(request)

    try:
        result = run_agent_turn(
            gemini_client=ai_client,
            conversation_history=conv_history,
            user_intent=user_intent,
            repo_path=repo_path,
            auto_execute_safe=auto_execute
        )

        # Save assistant message
        AgentMessage.objects.create(
            session_id=session_id,
            role="assistant",
            content=result["explanation"] or result["raw_response"]
        )

        # Save tool outputs
        for step in result.get("executed_steps", []):
            AgentMessage.objects.create(
                session_id=session_id,
                role="tool",
                content=f"Ran {step['command']}",
                command=step["command"],
                command_output=step["output"],
                safety_level=step["safety_level"]
            )

        return JsonResponse({
            "success": True,
            "result": result
        })
    except Exception as e:
        logger.exception("Agent turn execution failed")
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
def api_agent_approve(request):
    """Approve and execute a pending command in Agent mode."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    repo_path = _get_active_repo(request)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    args = data.get("args", [])
    cmd_str = data.get("command", "")
    session_id = data.get("session_id", "default")

    if not args and cmd_str:
        import shlex
        try:
            clean = cmd_str[4:].strip() if cmd_str.startswith("git ") else cmd_str
            args = shlex.split(clean)
        except Exception:
            args = cmd_str.split()

    res = run_git(args, cwd=repo_path)
    output = res.stdout if res.success else res.stderr

    safety_lvl = data.get("safety_level", "AUTHORIZED")
    AgentMessage.objects.create(
        session_id=session_id,
        role="tool",
        content=f"User authorized & executed: {cmd_str}",
        command=cmd_str,
        command_output=output,
        safety_level=safety_lvl
    )

    return JsonResponse({
        "success": res.success,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "returncode": res.returncode
    })


@csrf_exempt
def api_agent_reset(request):
    """Clear conversation history for Agent mode."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    session_id = request.POST.get("session_id", "default")
    AgentMessage.objects.filter(session_id=session_id).delete()
    return JsonResponse({"success": True})


@csrf_exempt
def api_secret_scan(request):
    """Run secret scanner on staged or working directory changes."""
    repo_path = _get_active_repo(request)
    diff = get_raw_staged_diff(repo_path) or get_raw_unstaged_diff(repo_path)
    config = ZitConfig.get_solo()
    allowlist = [a.strip() for a in config.secrets_allowlist.splitlines() if a.strip()]
    findings = scan_diff_content(diff, allowlist=allowlist)
    return JsonResponse({
        "success": True,
        "findings": [
            {"file": f.file, "line": f.line, "rule": f.rule_name, "preview": f.preview}
            for f in findings
        ]
    })


@csrf_exempt
def api_switch_repo(request):
    """Switch active working repository."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    new_path = data.get("path", "").strip()
    if not new_path or not os.path.exists(new_path):
        return JsonResponse({"success": False, "error": f"Directory '{new_path}' does not exist."})

    norm_path = os.path.abspath(new_path)
    is_valid = is_git_repo(norm_path)
    request.session["current_repo_path"] = norm_path

    return JsonResponse({
        "success": True,
        "path": norm_path,
        "is_git_repo": is_valid
    })


@csrf_exempt
def api_test_ai(request):
    """Test Gemini API connection with optional credentials/model in request payload."""
    api_key = None
    model = None

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            api_key = data.get("api_key", "").strip()
            model = data.get("model", "").strip()
        except Exception:
            api_key = request.POST.get("api_key", "").strip()
            model = request.POST.get("model", "").strip()

    if api_key or model:
        base_client = get_ai_client(request)
        test_key = api_key or base_client.api_key
        test_model = model or base_client.model
        ai_client = GeminiClient(api_key=test_key, model=test_model)
    else:
        ai_client = get_ai_client(request)

    result = ai_client.test_connection()
    return JsonResponse(result)


@csrf_exempt
def api_save_workflow(request):
    """Save a GitHub Actions workflow to disk (.github/workflows/<name>.yml)."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    repo_path = _get_active_repo(request)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    name = data.get("name", "ci").strip()
    yaml_content = data.get("yaml_content", "").strip()

    if not name or not yaml_content:
        return JsonResponse({"success": False, "error": "Name and YAML content are required."})

    target_dir = os.path.join(repo_path, ".github", "workflows")
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{name}.yml" if not name.endswith((".yml", ".yaml")) else name
    full_path = os.path.join(target_dir, filename)

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        # Also save in database preset
        WorkflowPreset.objects.update_or_create(
            name=name,
            defaults={"yaml_content": yaml_content, "workflow_type": "github_action"}
        )
        return JsonResponse({"success": True, "path": full_path})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
