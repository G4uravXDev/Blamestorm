import os
import json
import logging
from typing import Optional, List, Dict, Any
from .prompts import get_system_prompt, format_context

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-1.5-flash"


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or ""
        ).strip()
        self.model = model or DEFAULT_MODEL
        self._sdk_client = None

        if self.api_key:
            try:
                from google import genai
                self._sdk_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize google.genai Client: {e}. Will use REST fallback.")
                self._sdk_client = None

    def has_key(self) -> bool:
        return bool(self.api_key)

    def test_connection(self) -> Dict[str, Any]:
        """Test if the Gemini API key is valid and working."""
        if not self.has_key():
            return {
                "success": False,
                "error": "No Gemini API key configured. Please enter your key in Settings or set the GEMINI_API_KEY environment variable."
            }

        try:
            resp = self.generate(
                prompt="Respond with 'Blamestorm Gemini online' if you can read this.",
                system_instruction="You are a health checker. Reply in 3 words."
            )
            return {"success": True, "message": resp.strip(), "model": self.model}
        except Exception as e:
            return {"success": False, "error": str(e), "model": self.model}

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.4,
        max_output_tokens: int = 2048,
    ) -> str:
        """Generate content with Gemini using SDK or direct REST fallback."""
        if not self.has_key():
            raise ValueError(
                "Gemini API key is not configured. Please add your key in the Settings page or export GEMINI_API_KEY."
            )

        target_model = model or self.model

        # 1. Try google.genai SDK
        if self._sdk_client:
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
                if system_instruction:
                    config.system_instruction = system_instruction

                resp = self._sdk_client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config
                )
                if resp and resp.text:
                    return resp.text.strip()
            except Exception as e:
                logger.warning(f"SDK generation failed ({e}), attempting REST fallback.")

        # 2. REST API Fallback
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
        
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        
        if resp.status_code != 200:
            err_details = resp.text
            try:
                err_json = resp.json()
                err_details = err_json.get("error", {}).get("message", err_details)
            except Exception:
                pass
            raise RuntimeError(f"Gemini API error ({resp.status_code}): {err_details}")

        data = resp.json()
        try:
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        except Exception as e:
            raise RuntimeError(f"Failed to parse Gemini response: {e}")

        return ""

    def generate_commit_suggestions(self, staged_diff: str, stat_summary: str = "") -> List[str]:
        """
        Generate 3 conventional commit message suggestions from staged diff.
        """
        if not staged_diff or not staged_diff.strip():
            return [
                "feat: update project files",
                "chore: commit staged changes",
                "fix: minor updates and improvements"
            ]

        # Truncate diff if extremely large
        diff_snippet = staged_diff[:14000]
        prompt_parts = []
        if stat_summary and stat_summary.strip():
            prompt_parts.append(f"### UPDATED FILES INVENTORY & STATS:\n{stat_summary.strip()}")
        if diff_snippet and diff_snippet.strip():
            prompt_parts.append(f"### DETAILED CHANGES ACROSS ALL UPDATED FILES:\n{diff_snippet.strip()}")

        prompt_parts.append(
            "Go through all the updated files listed above. Understand the collective purpose and scope of the modifications, "
            "and output exactly 3 conventional commit suggestions (each on a new line prefixed with [SUGGESTION] )."
        )
        prompt = "\n\n".join(prompt_parts)

        sys_prompt = get_system_prompt("commit")
        try:
            output = self.generate(prompt=prompt, system_instruction=sys_prompt, temperature=0.3)
            suggestions = []
            for line in output.splitlines():
                clean = line.strip()
                if clean.startswith("[SUGGESTION]"):
                    s = clean.replace("[SUGGESTION]", "").strip()
                    if s:
                        suggestions.append(s)
                elif clean.startswith(("- ", "* ", "1. ", "2. ", "3. ")):
                    s = clean.lstrip("-*0123456789. ")
                    if s:
                        suggestions.append(s)
                elif clean and len(clean) < 100:
                    suggestions.append(clean)

            if suggestions:
                return suggestions[:3]
        except Exception as e:
            logger.error(f"Commit suggestion generation failed: {e}")
            raise e

        return [
            "feat: update application logic",
            "fix: correct issue in current branch",
            "chore: sync and organize files"
        ]

    def mentor_query(
        self,
        query_type: str,
        repo_status=None,
        recent_commits=None,
        user_message: str = "",
        extra_context: str = ""
    ) -> str:
        """Run an AI Mentor query (explain, error, recommend, learn, review, gitignore)."""
        sys_prompt = get_system_prompt(query_type)
        context_str = format_context(repo_status, recent_commits, extra_context)

        prompt = f"Repository Context:\n{context_str}\n\n"
        if user_message:
            prompt += f"User Request / Question:\n{user_message}\n"
        else:
            prompt += "Please provide your assessment and instructions based on the repository state.\n"

        return self.generate(prompt=prompt, system_instruction=sys_prompt, temperature=0.4)

    def resolve_conflict(self, file_path: str, conflict_text: str) -> str:
        """Request AI conflict resolution recommendations and resolved content."""
        sys_prompt = get_system_prompt("merge_resolve")
        prompt = f"File: {file_path}\n\nConflict Content with Markers:\n{conflict_text}\n\nAnalyze and provide resolution."
        return self.generate(prompt=prompt, system_instruction=sys_prompt, temperature=0.2)

    def mentor_code_turn(self, file_path: str, current_code: str, user_instruction: str, action: str = "custom") -> dict:
        """
        Analyze, explain, or update a specific file.
        Returns dict with: explanation, suggested_code, has_suggested_code.
        """
        sys_prompt = get_system_prompt("code_mentor")

        prompt = (
            f"Active File: {file_path}\n"
            f"Requested Action: {action}\n\n"
            f"Current File Content:\n"
            f"```\n{current_code[:25000]}\n```\n\n"
            f"User Instruction:\n{user_instruction}"
        )

        raw_resp = self.generate(prompt=prompt, system_instruction=sys_prompt, temperature=0.2)

        suggested_code = ""
        has_suggested_code = False

        if "```UPDATED_CODE" in raw_resp:
            parts = raw_resp.split("```UPDATED_CODE", 1)
            explanation = parts[0].strip()
            rest = parts[1]
            if "```" in rest:
                suggested_code = rest.split("```", 1)[0].strip()
                has_suggested_code = True
                after_code = rest.split("```", 1)[1].strip()
                if after_code:
                    explanation += "\n\n" + after_code
            else:
                suggested_code = rest.strip()
                has_suggested_code = True
        elif action in ("refactor", "update", "fix") and "```" in raw_resp:
            import re
            matches = list(re.finditer(r"```(?:\w+)?\n([\s\S]*?)```", raw_resp))
            if matches:
                longest = max(matches, key=lambda m: len(m.group(1)))
                suggested_code = longest.group(1).strip()
                has_suggested_code = True
                explanation = raw_resp.replace(longest.group(0), "[Suggested updated code loaded into the Right Box]").strip()
            else:
                explanation = raw_resp
        else:
            explanation = raw_resp

        return {
            "explanation": explanation.strip(),
            "suggested_code": suggested_code,
            "has_suggested_code": has_suggested_code,
            "raw_response": raw_resp
        }


def get_ai_client(request=None) -> GeminiClient:
    """Helper to instantiate GeminiClient from request session, DB config, or env."""
    api_key = None
    model = None

    if request and hasattr(request, "session"):
        api_key = request.session.get("gemini_api_key")
        model = request.session.get("gemini_model")

    if not api_key or not model:
        try:
            from ..models import ZitConfig
            config = ZitConfig.get_solo()
            if not api_key and config.gemini_api_key:
                api_key = config.gemini_api_key
            if not model and config.gemini_model:
                model = config.gemini_model
        except Exception:
            pass

    return GeminiClient(api_key=api_key, model=model or DEFAULT_MODEL)
