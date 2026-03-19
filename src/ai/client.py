"""AI client — sends page data to Claude/OpenAI for analysis and code generation."""

from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
from pathlib import Path

from rich.console import Console

from src.config import AppConfig
from src.analyzer.page_analyzer import SiteAnalysis

console = Console()


class AIClient:
    """Unified client for Claude and OpenAI APIs."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._claude = None
        self._openai = None
        self._init_clients()

    def _init_clients(self) -> None:
        provider = self.config.ai.provider
        if provider in ("claude", "both"):
            try:
                import anthropic
                self._claude = anthropic.Anthropic()
                console.print("[green]Claude API client initialized[/green]")
            except ImportError:
                console.print("[yellow]anthropic package not installed[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Claude API not available: {e}[/yellow]")

        if provider in ("openai", "both"):
            try:
                import openai
                self._openai = openai.OpenAI()
                console.print("[green]OpenAI API client initialized[/green]")
            except ImportError:
                console.print("[yellow]openai package not installed[/yellow]")
            except Exception as e:
                console.print(f"[yellow]OpenAI API not available: {e}[/yellow]")

    def _detect_media_type(self, file_path: str) -> str:
        """Detect image media type from file extension."""
        mime, _ = mimetypes.guess_type(file_path)
        if mime and mime.startswith("image/"):
            return mime
        return "image/png"  # Default

    async def analyze_screenshot(self, screenshot_path: str, context: str = "") -> str:
        """Send a screenshot to vision AI for structural analysis."""
        path = Path(screenshot_path)
        if not path.exists():
            return f"Screenshot not found: {screenshot_path}"

        img_data = path.read_bytes()
        if len(img_data) > 10 * 1024 * 1024:  # 10MB limit
            console.print(f"[yellow]Screenshot too large ({len(img_data)} bytes), skipping[/yellow]")
            return "Screenshot too large for API"

        img_b64 = base64.standard_b64encode(img_data).decode("utf-8")
        media_type = self._detect_media_type(screenshot_path)

        prompt = f"""Analyze this website screenshot. Describe:
1. Overall layout structure (sidebar, navbar, content areas)
2. UI components visible (buttons, tables, cards, forms, charts, etc.)
3. Color scheme and visual design patterns
4. Navigation structure
5. Content type and purpose of this page

{f'Additional context: {context}' if context else ''}

Be specific about positions, sizes, and relationships between elements."""

        if self._claude:
            return await self._call_claude_vision(img_b64, media_type, prompt)
        elif self._openai:
            return await self._call_openai_vision(img_b64, media_type, prompt)
        else:
            raise RuntimeError("No AI provider available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")

    async def generate_summary(self, analysis: SiteAnalysis, screenshot_analyses: list[str]) -> str:
        """Generate a comprehensive frontend structure summary."""
        analysis_json = json.dumps(analysis.to_dict(), indent=2, default=str)

        prompt = f"""You are a frontend architecture analyst. Based on the following data from crawling a website,
generate a thorough, structured summary of the website's frontend.

## Extracted Data (from DOM analysis)
```json
{analysis_json}
```

## Visual Analysis (from screenshots)
{chr(10).join(f'### Page {i+1}{chr(10)}{a}' for i, a in enumerate(screenshot_analyses))}

## Required Output Sections

### 1. Site Overview
### 2. Page Map
### 3. Layout Architecture
### 4. Component Library
### 5. Design System
### 6. Navigation & Routing
### 7. Interaction Patterns
### 8. Replication Recommendations

Be thorough and specific. This summary will be used to recreate the frontend."""

        if self._claude:
            return await self._call_claude_text(prompt)
        elif self._openai:
            return await self._call_openai_text(prompt)
        else:
            raise RuntimeError("No AI provider available.")

    async def generate_vue_component(self, component_info: str, design_context: str) -> str:
        """Generate a Vue 3 SFC from analysis data."""
        prompt = f"""Generate a Vue 3 Single File Component (.vue) that replicates the following component.

## Component Info
{component_info}

## Design Context
{design_context}

Requirements:
- Use Vue 3 Composition API with <script setup>
- Use scoped CSS
- Match the visual design as closely as possible
- Use semantic HTML

Return ONLY the .vue file content, no explanation."""

        if self._claude:
            return await self._call_claude_text(prompt)
        elif self._openai:
            return await self._call_openai_text(prompt)
        else:
            raise RuntimeError("No AI provider available.")

    async def _call_claude_vision(self, img_b64: str, media_type: str, prompt: str) -> str:
        """Call Claude API with an image."""
        return await asyncio.to_thread(self._call_claude_vision_sync, img_b64, media_type, prompt)

    def _call_claude_vision_sync(self, img_b64: str, media_type: str, prompt: str) -> str:
        client = self._claude
        try:
            message = client.messages.create(
                model=self.config.ai.claude_model,
                max_tokens=self.config.ai.max_tokens,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            if message.content:
                return message.content[0].text
            return "Empty response from Claude"
        except Exception as e:
            console.print(f"[red]Claude API error: {e}[/red]")
            return f"API error: {e}"

    async def _call_claude_text(self, prompt: str) -> str:
        """Call Claude API with text only."""
        return await asyncio.to_thread(self._call_claude_text_sync, prompt)

    def _call_claude_text_sync(self, prompt: str) -> str:
        client = self._claude
        try:
            message = client.messages.create(
                model=self.config.ai.claude_model,
                max_tokens=self.config.ai.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            if message.content:
                return message.content[0].text
            return "Empty response from Claude"
        except Exception as e:
            console.print(f"[red]Claude API error: {e}[/red]")
            return f"API error: {e}"

    async def _call_openai_vision(self, img_b64: str, media_type: str, prompt: str) -> str:
        """Call OpenAI API with an image."""
        return await asyncio.to_thread(self._call_openai_vision_sync, img_b64, media_type, prompt)

    def _call_openai_vision_sync(self, img_b64: str, media_type: str, prompt: str) -> str:
        client = self._openai
        try:
            response = client.chat.completions.create(
                model=self.config.ai.openai_model,
                max_tokens=self.config.ai.max_tokens,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:{media_type};base64,{img_b64}", "detail": "high"
                        }},
                    ],
                }],
            )
            if response.choices:
                return response.choices[0].message.content or "Empty response"
            return "No choices in response"
        except Exception as e:
            console.print(f"[red]OpenAI API error: {e}[/red]")
            return f"API error: {e}"

    async def _call_openai_text(self, prompt: str) -> str:
        """Call OpenAI API with text only."""
        return await asyncio.to_thread(self._call_openai_text_sync, prompt)

    def _call_openai_text_sync(self, prompt: str) -> str:
        client = self._openai
        try:
            response = client.chat.completions.create(
                model=self.config.ai.openai_model,
                max_tokens=self.config.ai.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            if response.choices:
                return response.choices[0].message.content or "Empty response"
            return "No choices in response"
        except Exception as e:
            console.print(f"[red]OpenAI API error: {e}[/red]")
            return f"API error: {e}"
