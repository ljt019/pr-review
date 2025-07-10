from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


@dataclass
class EmbeddingModel:
    """Wrapper around a transformer model returning mean-pooled embeddings."""

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str | None = None  # allow overriding in tests

    def __post_init__(self) -> None:
        # ------------------------------------------------------------------
        # Select device (prefer GPU) and load tokenizer/model
        # ------------------------------------------------------------------
        self.device = torch.device(self.device or ("cuda" if torch.cuda.is_available() else "cpu"))

        if self.device.type != "cuda":
            # Surface a helpful message so users know we're on CPU.
            print("🟡 GPU not available. Falling back to CPU for embedding model.")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        # Load model weights with appropriate dtype and move to device
        load_kwargs: dict = {}
        if self.device.type == "cuda":
            load_kwargs["torch_dtype"] = torch.float16  # save VRAM

        self.model = AutoModel.from_pretrained(self.model_name, **load_kwargs).to(self.device)
        self.model.eval()
        self.dim = self.model.config.hidden_size

    def encode(self, text: str) -> np.ndarray:
        """Return a single embedding vector for *text*."""
        with torch.no_grad():
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            outputs = self.model(**inputs)
            emb = outputs.last_hidden_state.mean(dim=1)
        return emb[0].cpu().numpy()


__all__ = ["EmbeddingModel"]
