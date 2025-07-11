from __future__ import annotations

"""Lightweight wrapper to load and run Qwen3 on GPU (fallback CPU).

This will be integrated in Milestone 3; providing it now ensures that the
LLM is initialised consistently with the embedding model.
"""

from dataclasses import dataclass
from typing import List, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

__all__ = ["Qwen3"]


@dataclass
class Qwen3:
    """Qwen3-Chat convenience wrapper with 4-bit quantization.

    Parameters
    ----------
    model_name:
        Hugging Face model ID. Defaults to the 7-B Qwen3-Chat checkpoint.
    use_quantization:
        Whether to use 4-bit quantization to reduce memory usage.
    device:
        Force a specific torch.device (e.g. "cuda:0"). Leave *None* to pick
        GPU if available or CPU otherwise.
    trust_remote_code:
        If the upstream model defines custom logic we need to allow it.
    """

    model_name: str = "Qwen/Qwen3-8B"  # Updated to use Qwen3-8B
    use_quantization: bool = True
    device: Optional[str] = None
    trust_remote_code: bool = True

    def __post_init__(self) -> None:
        # ------------------------------------------------------------------
        # Select device (prefer GPU) and load tokenizer
        # ------------------------------------------------------------------
        self.device = torch.device(self.device or ("cuda" if torch.cuda.is_available() else "cpu"))

        # Inform the user when we have to fall back to CPU
        if self.device.type != "cuda":
            print("🟡 GPU not available. Falling back to CPU for Qwen3 model.")
            # Disable quantization on CPU as BitsAndBytes requires CUDA
            self.use_quantization = False
        elif self.use_quantization:
            print("🟢 Loading Qwen3 model with 4-bit quantization to reduce memory usage.")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, trust_remote_code=self.trust_remote_code
        )

        # ------------------------------------------------------------------
        # Set up quantization config if using GPU
        # ------------------------------------------------------------------
        quantization_config = None
        if self.use_quantization and self.device.type == "cuda":
            try:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch.float16,
                )
            except ImportError:
                print("🟡 BitsAndBytes not available. Loading model without quantization.")
                self.use_quantization = False

        # ------------------------------------------------------------------
        # Load model with appropriate settings
        # ------------------------------------------------------------------
        load_kwargs = {
            "trust_remote_code": self.trust_remote_code,
        }

        if quantization_config is not None:
            load_kwargs["quantization_config"] = quantization_config
            load_kwargs["device_map"] = "auto"
        else:
            # No quantization - use standard loading
            if self.device.type == "cuda":
                load_kwargs["torch_dtype"] = torch.float16
                load_kwargs["device_map"] = "auto"
            else:
                load_kwargs["torch_dtype"] = torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            **load_kwargs,
        )

        # If we didn't rely on auto-placement, move the whole module now.
        if not self.use_quantization and self.device.type != "cuda":
            self.model.to(self.device)

        self.model.eval()

    # ------------------------------------------------------------------
    # Inference helpers
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 65536,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """Generate completion for *prompt* using greedy / nucleus sampling."""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        output_ids = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0,
            **kwargs,
        )

        text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        
        # Remove the original prompt from the output
        if text.startswith(prompt):
            text = text[len(prompt):].strip()
        
        if stop:
            for s in stop:
                idx = text.find(s)
                if idx != -1:
                    text = text[:idx]
        return text.strip() 