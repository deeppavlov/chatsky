"""
HuggingFace Cosine Model
--------------------------

This module provides an adapter interface for Huggingface models.
It leverages transformer embeddings to compute distances between utterances.
"""
from typing import Optional
from argparse import Namespace
from pathlib import Path

from ...huggingface import BaseHFModel, hf_available

try:
    import numpy as np
    from tokenizers import Tokenizer
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch

    hf_available = hf_available and True
except ImportError:
    np = Namespace(ndarray=None)
    torch = Namespace(device=None)
    Tokenizer = None
    PreTrainedModel = None
    hf_available = hf_available and False

from ....dataset import Dataset
from .cosine_matcher_mixin import CosineMatcherMixin


class HFMatcher(CosineMatcherMixin, BaseHFModel):
    """
    HFMatcher utilizes embeddings from Hugging Face models to measure
    proximity between utterances and pre-defined labels.

    :param model: A pretrained Hugging Face format model.
    :param tokenizer: A pretrained Hugging Face tokenizer.
    :param device: Pytorch device object. The device will be used for inference and pre-training.
    :param namespace_key: Name of the namespace in framework states that the model will be using.
    :param dataset: Labels for the matcher. The prediction output depends on proximity to different labels.
    :param tokenizer_kwargs: Default tokenizer arguments override.
    :param model_kwargs: Default model arguments override.
    """

    def __init__(
        self,
        model: AutoModelForSequenceClassification,
        tokenizer: Tokenizer,
        device: torch.device,
        namespace_key: str,
        dataset: Dataset,
        tokenizer_kwargs: Optional[dict] = None,
        model_kwargs: Optional[dict] = None,
    ) -> None:
        if not hf_available:
            raise ImportError("`huggingface` or `pytorch` missing. Try pip install dff[huggingface].")
        CosineMatcherMixin.__init__(self, dataset=dataset)
        BaseHFModel.__init__(self, model, tokenizer, device, namespace_key, tokenizer_kwargs, model_kwargs)

    def save(self, path: str, **kwargs) -> None:
        """
        :param path: Path to saving directory.
        :param kwargs: Keyword arguments are forwarded to the 'save_pretrained' method of the underlying model.
        """
        saving_path = Path(path)
        self.model.save_pretrained(saving_path, **kwargs)
        self.tokenizer.save_pretrained(saving_path)
        with (saving_path / f"{self.namespace_key}.json").open("w+", encoding="utf-8") as file:
            file.write(self.dataset.json())

    @classmethod
    def load(cls, path: str, namespace_key: str) -> __qualname__:
        saving_path = Path(path)
        model = AutoModelForSequenceClassification.from_pretrained(path)
        tokenizer = AutoTokenizer.from_pretrained(path)
        dataset = Dataset.parse_file(saving_path / f"{namespace_key}.json")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return cls(model=model, tokenizer=tokenizer, device=device, dataset=dataset, namespace_key=namespace_key)
