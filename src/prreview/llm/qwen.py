from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from prreview.review.context_selector import Chunk


@dataclass
class Qwen3Model:
    """Wrapper around a local Qwen model generating review text."""

    model_name: str = "Qwen/Qwen3-8B"
    max_model_tokens: int = 131072  # Qwen3's context limit

    def __post_init__(self) -> None:
        print(f"🤖 Loading {self.model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        
        # Load model with memory-efficient settings
        device = "cuda" if torch.cuda.is_available() else "cpu"
        load_kwargs = {
            "trust_remote_code": True,
            "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
            "low_cpu_mem_usage": True,
        }
        
        # For CPU, use 8-bit quantization to reduce memory usage
        if device == "cpu":
            try:
                load_kwargs["load_in_8bit"] = True
                print("💾 Using 8-bit quantization to reduce memory usage")
            except:
                print("⚠️  8-bit quantization not available, using full precision")
        
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, **load_kwargs)
        self.model.eval()
        print(f"✅ Model loaded on {device}")

    def _truncate_to_token_limit(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate and decode back to text
        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens, skip_special_tokens=True)

    def generate_review(self, diff: str, context: Iterable[Chunk], max_tokens: int = 256) -> str:
        """Return LLM-generated review text for *diff* and *context*."""
        # Reserve tokens for the prompt structure and generation
        reserved_tokens = max_tokens + 1000  # Extra buffer for prompt formatting
        available_tokens = self.max_model_tokens - reserved_tokens
        
        # Allocate tokens between diff and context (70% diff, 30% context)
        diff_token_budget = int(available_tokens * 0.7)
        context_token_budget = int(available_tokens * 0.3)
        
        # Truncate diff if needed
        diff_truncated = self._truncate_to_token_limit(diff, diff_token_budget)
        if len(self.tokenizer.encode(diff, add_special_tokens=False)) > diff_token_budget:
            print(f"⚠️  Diff truncated to fit token limit ({diff_token_budget} tokens)")
        
        # Build context with token budget
        ctx_blocks: List[str] = []
        context_so_far = ""
        
        for c in context:
            block = f"### {c.file_path}:{c.start_line}-{c.end_line}\n{c.text}\n"
            test_context = context_so_far + block
            
            # Check if adding this block would exceed budget
            if len(self.tokenizer.encode(test_context, add_special_tokens=False)) > context_token_budget:
                if ctx_blocks:  # We have at least some context
                    print(f"⚠️  Context truncated to fit token limit (included {len(ctx_blocks)} chunks)")
                    break
                else:  # Even the first chunk is too big, truncate it
                    truncated_text = self._truncate_to_token_limit(c.text, context_token_budget - 100)
                    ctx_blocks.append(f"### {c.file_path}:{c.start_line}-{c.end_line}\n{truncated_text}")
                    print(f"⚠️  First context chunk truncated to fit token limit")
                    break
            
            ctx_blocks.append(block)
            context_so_far = test_context
        
        # Build the prompt
        prompt = f"Review the following code changes:\n\nDiff:\n{diff_truncated}\n\nContext:\n" + "".join(ctx_blocks) + "\n\nProvide a concise review focusing on potential issues:\n"
        
        # Verify total size
        total_tokens = len(self.tokenizer.encode(prompt, add_special_tokens=True))
        if total_tokens > self.max_model_tokens - max_tokens:
            print(f"❌ Error: Even after truncation, prompt is too long ({total_tokens} tokens)")
            return "Error: Input too large for model even after truncation"
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        
        # Move inputs to the same device as the model
        if hasattr(self.model, 'device'):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        elif next(self.model.parameters()).is_cuda:
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            output = self.model.generate(**inputs, max_new_tokens=max_tokens)
        text = self.tokenizer.decode(output[0], skip_special_tokens=True)
        if text.startswith(prompt):
            text = text[len(prompt):]
        return text.strip()


__all__ = ["Qwen3Model"]
