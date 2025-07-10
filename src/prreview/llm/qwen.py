from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from prreview.review.context_selector import Chunk


@dataclass
class Qwen3Model:
    """Wrapper around a local Qwen3 model generating review text."""

    model_name: str = "Qwen/Qwen3-8B"

    def __post_init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, trust_remote_code=True)
        self.model.eval()

    def generate_review(self, diff: str, context: Iterable[Chunk], max_tokens: int = 256) -> str:
        """Return LLM-generated review text for *diff* and *context*."""
        ctx_blocks: List[str] = []
        for c in context:
            ctx_blocks.append(f"### {c.file_path}:{c.start_line}-{c.end_line}\n{c.text}")
        prompt = f"Diff:\n{diff}\n\nContext:\n" + "\n".join(ctx_blocks) + "\n\nReview:" 
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(**inputs, max_new_tokens=max_tokens)
        text = self.tokenizer.decode(output[0], skip_special_tokens=True)
        if text.startswith(prompt):
            text = text[len(prompt):]
        return text.strip()


__all__ = ["Qwen3Model"]
