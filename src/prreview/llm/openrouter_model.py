from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openai import OpenAI

from prreview.review.context_selector import Chunk


SYSTEM_MESSAGE = (
    "You are a precise code reviewer bot. Analyze the PR diff and context. "
    "First, think through your analysis in <think> tags, then provide a JSON"
    " response. Output ASCII JSON only." 
)


@dataclass
class OpenRouterModel:
    """Generate review text using OpenRouter's hosted model."""

    model_name: str = "qwen/qwen3-8b"

    def __post_init__(self) -> None:
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENROUTER_API_KEY")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON payload from text that may include <think> tags."""
        import re

        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        return json_match.group(0) if json_match else cleaned

    def generate_review(
        self, diff: str, context: Iterable[Chunk], max_tokens: int = 2048
    ) -> dict:
        ctx = [f"### {c.file_path}:{c.start_line}-{c.end_line}\n{c.text}" for c in context]
        user_msg = (
            "Review this PR:\n\nDiff:\n" + diff + "\n\nContext:\n" + "".join(ctx) +
            "\n\nOutput valid JSON with ASCII characters only."
        )
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_msg},
        ]
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content.strip()
        try:
            review = json.loads(self._extract_json_from_response(text))
        except json.JSONDecodeError:
            review = {"summary": "Error generating review", "actionable_comments": [], "nitpick_comments": []}
        output_dir = Path(".output")
        output_dir.mkdir(exist_ok=True)
        with open(output_dir / "review.json", "w", encoding="utf-8") as f:
            json.dump(review, f, indent=2, ensure_ascii=True)
        return review


__all__ = ["OpenRouterModel"]
