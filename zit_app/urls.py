from django.urls import path
from . import views

app_name = "zit"

urlpatterns = [
    # UI Views
    path("", views.dashboard_view, name="dashboard"),
    path("staging/", views.staging_view, name="staging"),
    path("commit/", views.commit_view, name="commit"),
    path("branches/", views.branches_view, name="branches"),
    path("timeline/", views.timeline_view, name="timeline"),
    path("time-travel/", views.time_travel_view, name="time_travel"),
    path("reflog/", views.reflog_view, name="reflog"),
    path("stash/", views.stash_view, name="stash"),
    path("merge/", views.merge_resolve_view, name="merge_resolve"),
    path("bisect/", views.bisect_view, name="bisect"),
    path("cherry-pick/", views.cherry_pick_view, name="cherry_pick"),
    path("workflow/", views.workflow_builder_view, name="workflow_builder"),
    path("github/", views.github_view, name="github"),
    path("mentor/", views.ai_mentor_view, name="ai_mentor"),
    path("staging/mentor/", views.ai_code_studio_view, name="ai_code_mentor"),
    path("agent/", views.agent_view, name="agent"),
    path("settings/", views.settings_view, name="settings"),

    # API Endpoints (AJAX)
    path("api/git-command/", views.api_git_command, name="api_git_command"),
    path("api/ai-commit/", views.api_ai_commit, name="api_ai_commit"),
    path("api/ai-mentor/", views.api_ai_mentor, name="api_ai_mentor"),
    path("api/ai-code-mentor/query/", views.api_ai_code_mentor_query, name="api_ai_code_mentor_query"),
    path("api/ai-code-mentor/apply/", views.api_ai_code_mentor_apply, name="api_ai_code_mentor_apply"),
    path("api/ai-resolve/", views.api_ai_resolve, name="api_ai_resolve"),
    path("api/agent-turn/", views.api_agent_turn, name="api_agent_turn"),
    path("api/agent-approve/", views.api_agent_approve, name="api_agent_approve"),
    path("api/agent-reset/", views.api_agent_reset, name="api_agent_reset"),
    path("api/secret-scan/", views.api_secret_scan, name="api_secret_scan"),
    path("api/switch-repo/", views.api_switch_repo, name="api_switch_repo"),
    path("api/test-ai/", views.api_test_ai, name="api_test_ai"),
    path("api/save-workflow/", views.api_save_workflow, name="api_save_workflow"),
]
