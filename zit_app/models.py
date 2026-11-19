from django.db import models


class ZitConfig(models.Model):
    """Local configuration options for zit."""
    gemini_api_key = models.CharField(max_length=255, blank=True, default="")
    gemini_model = models.CharField(max_length=64, default="gemini-2.5-flash")
    confirm_destructive = models.BooleanField(default=True)
    auto_scan_secrets = models.BooleanField(default=True)
    secrets_allowlist = models.TextField(blank=True, default="")
    active_repo_path = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Zit Config ({self.gemini_model})"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class WorkflowPreset(models.Model):
    """Saved custom workflows (GitHub Actions or Git Ops)."""
    name = models.CharField(max_length=120)
    workflow_type = models.CharField(max_length=32, default="github_action")  # 'github_action' or 'git_ops'
    triggers = models.CharField(max_length=255, default="push,pull_request")
    yaml_content = models.TextField(blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class AgentMessage(models.Model):
    """Persistent chat history for AI Agent mode."""
    session_id = models.CharField(max_length=64, default="default")
    role = models.CharField(max_length=20)  # user, assistant, system, tool
    content = models.TextField()
    command = models.CharField(max_length=500, blank=True, default="")
    command_output = models.TextField(blank=True, default="")
    safety_level = models.CharField(max_length=20, default="SAFE")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.role}] {self.content[:30]}..."
