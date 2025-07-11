from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import tiktoken

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
    max_context_tokens: int = 128000  # Default context window for most models

    def __post_init__(self) -> None:
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENROUTER_API_KEY")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        
        # Initialize tokenizer for token counting
        # Use a compatible tokenizer for most models
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except KeyError:
            # Fallback to cl100k_base encoding (used by GPT-4/GPT-3.5)
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in the given text."""
        # Disable special token checking to handle any special tokens in code
        return len(self.tokenizer.encode(text, disallowed_special=()))

    def _truncate_to_token_limit(self, text: str, token_limit: int) -> str:
        """Truncate text to fit within token limit."""
        if self._count_tokens(text) <= token_limit:
            return text
        
        # Binary search to find the maximum length that fits
        lines = text.splitlines()
        if not lines:
            return ""
        
        low, high = 0, len(lines)
        best_text = ""
        
        while low <= high:
            mid = (low + high) // 2
            candidate = "\n".join(lines[:mid])
            
            if self._count_tokens(candidate) <= token_limit:
                best_text = candidate
                low = mid + 1
            else:
                high = mid - 1
        
        return best_text

    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON payload from text that may include <think> tags."""
        # Fix common character substitutions that might occur
        text = text.replace('ä', '{').replace('å', '}').replace('Ä', '[').replace('Å', ']').replace('Ö', '::')
        
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        return json_match.group(0) if json_match else cleaned

    def generate_review(
        self, diff: str, context: Iterable[Chunk], max_tokens: int = 2048
    ) -> dict:
        # Reserve tokens for the prompt structure and generation
        reserved_tokens = max_tokens + 1000  # Extra buffer for prompt formatting
        available_tokens = self.max_context_tokens - reserved_tokens
        
        # Count tokens in system message
        system_tokens = self._count_tokens(SYSTEM_MESSAGE)
        base_user_msg = "Review this PR:\n\nDiff:\n{}\n\nContext:\n{}\n\nOutput valid JSON with ASCII characters only."
        base_tokens = self._count_tokens(base_user_msg.format("", ""))
        
        # Allocate remaining tokens between diff and context (70% diff, 30% context)
        remaining_tokens = available_tokens - system_tokens - base_tokens
        diff_token_budget = int(remaining_tokens * 0.7)
        context_token_budget = int(remaining_tokens * 0.3)
        
        # Count raw diff tokens and provide feedback
        diff_tokens_raw = self._count_tokens(diff)
        print(f"📊 Raw diff size: {diff_tokens_raw:,} tokens")
        
        if diff_tokens_raw > 50000:
            print(f"⚠️  This is a very large diff! Consider breaking it into smaller PRs for better reviews.")
        
        # Truncate diff if needed
        diff_truncated = self._truncate_to_token_limit(diff, diff_token_budget)
        if diff_tokens_raw > diff_token_budget:
            print(f"⚠️  Diff truncated to fit token limit ({diff_token_budget} tokens)")
        
        # Build context with token budget
        ctx_blocks: List[str] = []
        context_tokens_used = 0
        
        for c in context:
            block = f"### {c.file_path}:{c.start_line}-{c.end_line}\n{c.text}\n"
            block_tokens = self._count_tokens(block)
            
            # Check if adding this block would exceed budget
            if context_tokens_used + block_tokens > context_token_budget:
                if ctx_blocks:  # We have at least some context
                    print(f"⚠️  Context truncated to fit token limit (included {len(ctx_blocks)} chunks)")
                    break
                else:  # Even the first chunk is too big, truncate it
                    truncated_text = self._truncate_to_token_limit(
                        c.text, context_token_budget - 100
                    )
                    truncated_block = f"### {c.file_path}:{c.start_line}-{c.end_line}\n{truncated_text}\n"
                    ctx_blocks.append(truncated_block)
                    context_tokens_used += self._count_tokens(truncated_block)
                    print(f"⚠️  First context chunk truncated to fit token limit")
                    break
            
            ctx_blocks.append(block)
            context_tokens_used += block_tokens
        
        # Build the final user message
        user_msg = base_user_msg.format(diff_truncated, "".join(ctx_blocks))
        
        # Verify total size
        total_tokens = self._count_tokens(SYSTEM_MESSAGE) + self._count_tokens(user_msg)
        print(f"📊 Total prompt tokens: {total_tokens:,} (limit: {self.max_context_tokens - max_tokens})")
        
        if total_tokens > self.max_context_tokens - max_tokens:
            print(f"⚠️  Warning: Prompt may still be too large for model context window")
        
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_msg},
        ]
        
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=max_tokens,
                extra_body={
                    "provider": {
                        "order": ["Groq"]
                    }
                }
            )
            text = resp.choices[0].message.content.strip()
            
            try:
                review = json.loads(self._extract_json_from_response(text))
            except json.JSONDecodeError:
                review = {"summary": "Error parsing JSON response", "actionable_comments": [], "nitpick_comments": []}
                
        except Exception as e:
            print(f"❌ Error calling OpenRouter API: {e}")
            review = {"summary": "Error generating review", "actionable_comments": [], "nitpick_comments": []}
        
        output_dir = Path(".output")
        output_dir.mkdir(exist_ok=True)
        with open(output_dir / "review.json", "w", encoding="utf-8") as f:
            json.dump(review, f, indent=2, ensure_ascii=True)
        
        return review


__all__ = ["OpenRouterModel"]
