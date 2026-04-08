"""Client for optional LLM synthesis of the final competitive report."""

from __future__ import annotations

import asyncio
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.analysis.competitive_report import CompetitiveSynthesis
from src.analysis.prompts import build_synthesis_system_prompt, build_synthesis_user_prompt
from src.config import SynthesisConfig


class CompetitiveSynthesisClient:
    """Thin wrapper around an OpenAI-compatible text generation API."""

    def __init__(self, config: SynthesisConfig):
        self.config = config

    async def synthesize(
        self,
        competitive_analysis: dict,
        page_insights: dict[str, dict],
        extraction_results: dict[str, dict],
    ) -> CompetitiveSynthesis:
        """Return an optional synthesized competitive report."""
        if not self.config.enabled:
            return CompetitiveSynthesis()
        if self.config.provider.lower() != "openai":
            return CompetitiveSynthesis(
                risks_and_unknowns=[f"unsupported synthesis provider: {self.config.provider}"]
            )

        api_key = self._resolve_api_key()
        if not api_key:
            return CompetitiveSynthesis(
                risks_and_unknowns=[f"missing api key in {self.config.api_key_env} or SYNTHESIS_API_KEY"]
            )

        try:
            return await asyncio.to_thread(
                self._request_openai_synthesis,
                competitive_analysis,
                page_insights,
                extraction_results,
                api_key,
            )
        except Exception as e:
            return CompetitiveSynthesis(risks_and_unknowns=[f"synthesis_error: {e}"])

    def _resolve_api_key(self) -> str:
        """Resolve API key from generic or provider-specific environment variables."""
        return os.environ.get("SYNTHESIS_API_KEY") or os.environ.get(self.config.api_key_env, "")

    def _resolve_base_url(self) -> str:
        """Resolve base URL from env override or config."""
        return os.environ.get("SYNTHESIS_API_BASE_URL") or self.config.api_base_url

    def _request_openai_synthesis(
        self,
        competitive_analysis: dict,
        page_insights: dict[str, dict],
        extraction_results: dict[str, dict],
        api_key: str,
    ) -> CompetitiveSynthesis:
        """Call an OpenAI-compatible chat-completions endpoint for synthesis."""
        payload = {
            "model": self.config.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": build_synthesis_system_prompt()},
                {
                    "role": "user",
                    "content": build_synthesis_user_prompt(
                        competitive_analysis,
                        page_insights,
                        extraction_results,
                    ),
                },
            ],
        }

        endpoint = self._resolve_base_url().rstrip("/") + "/chat/completions"
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.config.timeout_ms / 1000) as response:
                body = response.read().decode("utf-8")
        except HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"http {e.code}: {error_body}") from e
        except URLError as e:
            raise RuntimeError(f"network error: {e}") from e

        raw = json.loads(body)
        content = raw["choices"][0]["message"]["content"]
        parsed = self._parse_content(content)

        try:
            return CompetitiveSynthesis.model_validate(parsed)
        except Exception as e:
            return CompetitiveSynthesis(risks_and_unknowns=[f"synthesis_parse_error: {e}"])

    def _parse_content(self, content: object) -> dict:
        """Parse JSON content from chat completion output."""
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
            text = "\n".join(text_parts).strip()
        else:
            raise ValueError("unexpected synthesis response content shape")

        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()

        return json.loads(text)
