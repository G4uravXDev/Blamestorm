import re
import shlex
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .prompts import get_system_prompt, format_context
from .gemini_client import GeminiClient
from ..git_engine.runner import run_git, GitResult
from ..git_engine.status import get_status
from ..git_engine.log import get_commit_history


@dataclass
class AgentStep:
    command: str
    args: List[str]
    description: str
    safety_level: str  # SAFE, CAUTION, DESTRUCTIVE
    requires_approval: bool
    status: str = "pending"  # pending, running, success, failed, skipped
    output: str = ""
    exit_code: int = 0


@dataclass
class AgentPlan:
    explanation: str
    steps: List[AgentStep] = field(default_factory=list)
    is_done: bool = False
    raw_response: str = ""


DESTRUCTIVE_PATTERNS = [
    r"--hard",
    r"--force",
    r"-f\b",
    r"clean\s+-[a-zA-Z]*f",
    r"branch\s+-D",
    r"push.*--delete",
    r"reset\s+--hard",
]

READ_ONLY_COMMANDS = {
    "status", "log", "diff", "branch", "remote", "show", "tag", "reflog", "rev-parse", "config"
}


def classify_command_safety(args: List[str]) -> str:
    """Classify git command as SAFE, CAUTION, DESTRUCTIVE, or COMMIT_APPROVAL_REQUIRED."""
    if not args:
        return "SAFE"

    cmd_str = " ".join(args)
    for pat in DESTRUCTIVE_PATTERNS:
        if re.search(pat, cmd_str):
            return "DESTRUCTIVE"

    subcmd = args[0].lower() if args else ""

    # Strictly protect commits: AI must NEVER commit on its own; only the user can commit.
    if subcmd == "commit" or "commit" in args:
        return "COMMIT_APPROVAL_REQUIRED"

    if subcmd in READ_ONLY_COMMANDS and not any(flag in cmd_str for flag in ("-d", "-D", "--delete")):
        return "SAFE"

    return "CAUTION"


def parse_agent_response(response_text: str) -> AgentPlan:
    """
    Parse Gemini's response extracting [TOOL_USE] git commands.
    """
    lines = response_text.splitlines()
    steps: List[AgentStep] = []
    explanation_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[TOOL_USE]"):
            cmd_part = stripped.replace("[TOOL_USE]", "").strip()
            # Remove leading 'git ' if present
            if cmd_part.startswith("git "):
                cmd_part = cmd_part[4:].strip()

            try:
                # Safely split into arguments
                args = shlex.split(cmd_part, posix=False)
            except Exception:
                args = cmd_part.split()

            safety = classify_command_safety(args)
            # Both destructive operations and any commit operation strictly require user approval
            requires_approval = (safety in ("DESTRUCTIVE", "COMMIT_APPROVAL_REQUIRED"))

            desc = f"Execute git {cmd_part}"
            if safety == "COMMIT_APPROVAL_REQUIRED":
                desc = "Commit requires manual user authorization. Only you can commit."

            steps.append(AgentStep(
                command=f"git {cmd_part}",
                args=args,
                description=desc,
                safety_level=safety,
                requires_approval=requires_approval
            ))
        else:
            explanation_lines.append(line)

    explanation = "\n".join(explanation_lines).strip()
    is_done = "Done." in explanation or (len(steps) == 0 and len(explanation) > 0)

    return AgentPlan(
        explanation=explanation,
        steps=steps,
        is_done=is_done,
        raw_response=response_text
    )


def run_agent_turn(
    gemini_client: GeminiClient,
    conversation_history: List[Dict[str, str]],
    user_intent: str,
    repo_path: Optional[str] = None,
    auto_execute_safe: bool = True
) -> Dict[str, Any]:
    """
    Executes a single turn of the agent:
    1. Gathers current repo context
    2. Builds prompt with history + user intent
    3. Calls Gemini
    4. Parses tool use commands
    5. Optionally executes SAFE commands immediately
    6. Returns response, steps, outputs, and whether user approval is required
    """
    # 1. Repo context
    status = get_status(repo_path)
    recent = get_commit_history(max_count=5, cwd=repo_path)
    context_str = format_context(status, recent)

    # 2. Build conversation context
    sys_prompt = get_system_prompt("agent")
    
    prompt_builder = [
        f"--- CURRENT REPOSITORY STATUS ---\n{context_str}\n---------------------------------",
        "\n--- CONVERSATION HISTORY ---"
    ]

    for msg in conversation_history[-10:]:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        prompt_builder.append(f"[{role}]: {content}")

    if user_intent:
        prompt_builder.append(f"\n[USER REQUEST]: {user_intent}")

    prompt = "\n".join(prompt_builder)

    # 3. Call Gemini
    response_text = gemini_client.generate(
        prompt=prompt,
        system_instruction=sys_prompt,
        temperature=0.3
    )

    # 4. Parse plan
    plan = parse_agent_response(response_text)

    executed_steps = []
    pending_approval = None

    for step in plan.steps:
        subcmd = step.args[0].lower() if step.args else ""
        # Commits MUST NEVER be executed automatically. Only the user can commit.
        if subcmd == "commit" or "commit" in step.args:
            step.requires_approval = True
            step.safety_level = "COMMIT_APPROVAL_REQUIRED"
            step.description = "Commit requires manual user authorization. Only you can commit."

        if step.requires_approval or (not auto_execute_safe and step.safety_level != "SAFE"):
            pending_approval = {
                "command": step.command,
                "args": step.args,
                "safety_level": step.safety_level,
                "description": step.description
            }
            # Stop further auto-execution until user approves
            break
        else:
            # Execute step
            res = run_git(step.args, cwd=repo_path)
            step.status = "success" if res.success else "failed"
            step.output = res.stdout if res.success else res.stderr
            step.exit_code = res.returncode
            executed_steps.append({
                "command": step.command,
                "output": step.output,
                "status": step.status,
                "safety_level": step.safety_level,
                "exit_code": step.exit_code
            })

            if not res.success:
                # Command failed: stop and report
                break

    return {
        "explanation": plan.explanation,
        "raw_response": plan.raw_response,
        "is_done": plan.is_done,
        "executed_steps": executed_steps,
        "pending_approval": pending_approval,
        "total_planned_steps": len(plan.steps)
    }
