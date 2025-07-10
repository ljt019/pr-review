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

    def __post_init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.eval()
        self.dim = self.model.config.hidden_size

    def encode(self, text: str) -> np.ndarray:
        """Return a single embedding vector for *text*."""
        with torch.no_grad():
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            outputs = self.model(**inputs)
            emb = outputs.last_hidden_state.mean(dim=1)
        return emb[0].cpu().numpy()


__all__ = ["EmbeddingModel"]
