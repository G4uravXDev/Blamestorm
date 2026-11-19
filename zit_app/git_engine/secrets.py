import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

BINARY_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "bmp", "ico", "svg", "webp",
    "mp3", "mp4", "wav", "avi", "mov", "mkv",
    "zip", "tar", "gz", "bz2", "xz", "7z", "rar",
    "exe", "dll", "so", "dylib", "o", "a",
    "woff", "woff2", "ttf", "otf", "eot",
    "pdf", "doc", "docx", "xls", "xlsx",
    "pyc", "class", "wasm", "lock"
}


@dataclass
class SecretFinding:
    file: str
    line: int
    rule_name: str
    preview: str


DEFAULT_SECRET_RULES: List[Tuple[str, str]] = [
    # Cloud Provider Keys
    ("AWS Access Key ID", r"(?:^|[^A-Za-z0-9/+=])(AKIA[0-9A-Z]{16})(?:$|[^A-Za-z0-9/+=])"),
    ("AWS Secret Access Key", r"(?i)(?:aws_secret_access_key|aws_secret)\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"),
    ("Google API Key", r"(?:^|[^A-Za-z0-9])(AIza[0-9A-Za-z\-_]{35})(?:$|[^A-Za-z0-9])"),
    # Git Platform Tokens
    ("GitHub Personal Access Token", r"(?:^|[^A-Za-z0-9_])(ghp_[a-zA-Z0-9]{36})(?:$|[^A-Za-z0-9_])"),
    ("GitHub OAuth Token", r"(?:^|[^A-Za-z0-9_])(gho_[a-zA-Z0-9]{36})(?:$|[^A-Za-z0-9_])"),
    ("GitHub App Token", r"(?:^|[^A-Za-z0-9_])((?:ghu|ghs|ghr)_[a-zA-Z0-9]{36})(?:$|[^A-Za-z0-9_])"),
    ("GitHub Fine-Grained PAT", r"(?:^|[^A-Za-z0-9_])(github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})(?:$|[^A-Za-z0-9_])"),
    ("GitLab Personal Access Token", r"(?:^|[^A-Za-z0-9\-])(glpat-[a-zA-Z0-9\-]{20,})(?:$|[^A-Za-z0-9\-])"),
    # Communication Tokens
    ("Slack Token", r"(?:^|[^A-Za-z0-9\-])(xox[baprs]-[a-zA-Z0-9\-]{10,})(?:$|[^A-Za-z0-9\-])"),
    ("Slack Webhook URL", r"https://hooks\.slack\.com/services/T[0-9A-Z]+/B[0-9A-Z]+/[0-9A-Za-z]+"),
    ("Discord Bot Token", r"(?:^|[^A-Za-z0-9\.])([MN][A-Za-z0-9]{23,}\.[A-Za-z0-9\-_]{6}\.[A-Za-z0-9\-_]{27,})(?:$|[^A-Za-z0-9\.])"),
    ("Discord Webhook URL", r"https://discord(?:app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9\-_]+"),
    # Payment Tokens
    ("Stripe Secret Key", r"(?:^|[^A-Za-z0-9_])(sk_live_[a-zA-Z0-9]{24,})(?:$|[^A-Za-z0-9_])"),
    ("Stripe Restricted Key", r"(?:^|[^A-Za-z0-9_])(rk_live_[a-zA-Z0-9]{24,})(?:$|[^A-Za-z0-9_])"),
    # AI Providers
    ("OpenAI API Key", r"(?:^|[^A-Za-z0-9_])(sk-[a-zA-Z0-9]{32,48})(?:$|[^A-Za-z0-9_])"),
    ("Anthropic API Key", r"(?:^|[^A-Za-z0-9_])(sk-ant-[a-zA-Z0-9_\-]{32,})(?:$|[^A-Za-z0-9_])"),
    ("HuggingFace Token", r"(?:^|[^A-Za-z0-9_])(hf_[a-zA-Z0-9]{34,})(?:$|[^A-Za-z0-9_])"),
    # Cryptographic Material
    ("Private Key", r"-----BEGIN[A-Z\s]*PRIVATE KEY-----"),
    # JWT
    ("JWT Token", r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}"),
    # Database Connection Strings
    ("Database Connection String", r"(?i)(?:postgres|postgresql|mysql|mongodb|redis)://[^\s:]+:[^\s@]+@[^\s]+"),
    # Generic Secrets
    ("Generic API Key Assignment", r"(?i)(?:api[_\-]?key|apikey)\s*[:=]\s*['\"]([A-Za-z0-9\-_./+=]{8,})['\"]"),
    ("Generic Secret Assignment", r"(?i)(?:secret|secret[_\-]?key)\s*[:=]\s*['\"]([A-Za-z0-9\-_./+=]{8,})['\"]"),
    ("Generic Password Assignment", r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]{8,})['\"]"),
    ("Generic Token Assignment", r"(?i)(?:auth[_\-]?token|access[_\-]?token|bearer)\s*[:=]\s*['\"]([A-Za-z0-9\-_./+=]{8,})['\"]"),
]

COMPILED_RULES = [(name, re.compile(pat)) for name, pat in DEFAULT_SECRET_RULES]


def is_binary(path: str) -> bool:
    """Check if file extension indicates a binary file."""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return ext in BINARY_EXTENSIONS


def redact_match(matched: str) -> str:
    """Safely redact secret preview."""
    s = matched.strip()
    if len(s) <= 4:
        return "****"
    return f"{s[:4]}****"


def scan_diff_content(diff: str, allowlist: Optional[List[str]] = None) -> List[SecretFinding]:
    """Scan only added lines in a unified diff string."""
    findings: List[SecretFinding] = []
    current_file = ""
    line_in_new = 0
    allowlist = allowlist or []

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.replace("+++ b/", "", 1).strip()
        elif line.startswith("@@ "):
            plus_part = line.split("+")[1] if "+" in line else ""
            if plus_part:
                num_str = plus_part.split(",")[0].strip()
                try:
                    line_in_new = int(num_str)
                except ValueError:
                    line_in_new = 1
        elif line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:]
            if current_file and not is_binary(current_file):
                for name, reg in COMPILED_RULES:
                    m = reg.search(added_content)
                    if m:
                        secret_preview = redact_match(m.group(0))
                        findings.append(SecretFinding(
                            file=current_file,
                            line=line_in_new,
                            rule_name=name,
                            preview=secret_preview
                        ))
            line_in_new += 1
        elif not line.startswith("-") and not line.startswith("---"):
            if not line.startswith("diff ") and not line.startswith("index "):
                line_in_new += 1

    # Filter allowlisted findings
    if allowlist:
        findings = [
            f for f in findings
            if not any(a in f.preview or a in f.file or a in f.rule_name for a in allowlist)
        ]

    return findings


def scan_file_content(path: str, content: str, allowlist: Optional[List[str]] = None) -> List[SecretFinding]:
    """Scan full text content of a file."""
    if is_binary(path):
        return []

    findings: List[SecretFinding] = []
    allowlist = allowlist or []

    for lineno, line in enumerate(content.splitlines(), start=1):
        for name, reg in COMPILED_RULES:
            m = reg.search(line)
            if m:
                findings.append(SecretFinding(
                    file=path,
                    line=lineno,
                    rule_name=name,
                    preview=redact_match(m.group(0))
                ))

    if allowlist:
        findings = [
            f for f in findings
            if not any(a in f.preview or a in f.file or a in f.rule_name for a in allowlist)
        ]

    return findings
