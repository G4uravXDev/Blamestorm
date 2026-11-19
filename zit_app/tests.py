import os
from django.test import TestCase, Client
from django.urls import reverse

from .git_engine.runner import is_git_repo, get_repo_root, run_git
from .git_engine.status import get_status
from .git_engine.diff import parse_diff_output
from .git_engine.secrets import scan_diff_content, scan_file_content, redact_match
from .ai_engine.prompts import get_system_prompt, format_context
from .ai_engine.agent_runner import classify_command_safety, parse_agent_response
from .models import ZitConfig


class GitEngineTests(TestCase):
    def test_secret_scanner(self):
        sample_diff = (
            "diff --git a/config.py b/config.py\n"
            "--- a/config.py\n"
            "+++ b/config.py\n"
            "@@ -1,3 +1,4 @@\n"
            '+AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
            '+GOOGLE_KEY = "AIza' + 'B' * 35 + '"\n'
            '+GITHUB_PAT = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"\n'
        )
        findings = scan_diff_content(sample_diff)
        self.assertGreaterEqual(len(findings), 3)
        rules = [f.rule_name for f in findings]
        self.assertIn("AWS Access Key ID", rules)
        self.assertIn("Google API Key", rules)
        self.assertIn("GitHub Personal Access Token", rules)

    def test_secret_redaction(self):
        self.assertEqual(redact_match("AKIAIOSFODNN7EXAMPLE"), "AKIA****")
        self.assertEqual(redact_match("abc"), "****")

    def test_diff_parser(self):
        sample_diff = """diff --git a/test.txt b/test.txt
index 0000000..e69de29
--- a/test.txt
+++ b/test.txt
@@ -0,0 +1,2 @@
+hello
+world
"""
        diffs = parse_diff_output(sample_diff)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].path, "test.txt")
        self.assertEqual(diffs[0].additions, 2)
        self.assertEqual(len(diffs[0].hunks), 1)

    def test_agent_safety_classification(self):
        self.assertEqual(classify_command_safety(["status"]), "SAFE")
        self.assertEqual(classify_command_safety(["log", "--oneline"]), "SAFE")
        self.assertEqual(classify_command_safety(["diff"]), "SAFE")
        self.assertEqual(classify_command_safety(["add", "-A"]), "CAUTION")
        self.assertEqual(classify_command_safety(["commit", "-m", "msg"]), "CAUTION")
        self.assertEqual(classify_command_safety(["reset", "--hard", "HEAD~1"]), "DESTRUCTIVE")
        self.assertEqual(classify_command_safety(["push", "--force"]), "DESTRUCTIVE")
        self.assertEqual(classify_command_safety(["clean", "-fd"]), "DESTRUCTIVE")

    def test_agent_response_parsing(self):
        sample_llm_response = """I will inspect the repository first.
[TOOL_USE] git status
[TOOL_USE] git log -n 1
Then I will report back."""
        plan = parse_agent_response(sample_llm_response)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].command, "git status")
        self.assertEqual(plan.steps[1].command, "git log -n 1")

    def test_system_prompts(self):
        self.assertIn("conventional commit", get_system_prompt("commit"))
        self.assertIn("Git mentor", get_system_prompt("explain"))
        self.assertIn("[TOOL_USE]", get_system_prompt("agent"))


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_all_views_render(self):
        views_to_test = [
            "zit:dashboard",
            "zit:staging",
            "zit:commit",
            "zit:branches",
            "zit:timeline",
            "zit:time_travel",
            "zit:reflog",
            "zit:stash",
            "zit:merge_resolve",
            "zit:bisect",
            "zit:cherry_pick",
            "zit:workflow_builder",
            "zit:github",
            "zit:ai_mentor",
            "zit:agent",
            "zit:settings",
        ]
        for v in views_to_test:
            resp = self.client.get(reverse(v))
            self.assertEqual(resp.status_code, 200, f"View {v} failed with status {resp.status_code}")
