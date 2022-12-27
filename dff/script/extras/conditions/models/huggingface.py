"""
Base HF Model
--------------

This module provides a base class for matchers and classifiers
built on top of Hugging Face models.
"""
from argparse import Namespace
from typing import Optional
from collections.abc import Iterable

try:
    import numpy as np
    from tokenizers import Tokenizer
    from transformers.modeling_utils import PreTrainedModel
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch

    hf_available = True
except ImportError:
    np = Namespace(ndarray=None)
    torch = Namespace(device=None)
    Tokenizer = None
    PreTrainedModel = None
    hf_available = False

from .base_model import BaseModel
from ..dataset import Dataset


class BaseHFModel(BaseModel):
    """
    Base class for Hugging Face-based models.

    :param model: A pretrained Hugging Face format model.
    :param tokenizer: A pretrained Hugging Face tokenizer.
    :param device: Pytorch device object. The device will be used for inference and pre-training.
    :param namespace_key: Name of the namespace in framework states that the model will be using.
    :param tokenizer_kwargs: Default tokenizer arguments override.
    :param model_kwargs: Default model arguments override.
    """

    def __init__(
        self,
        model: PreTrainedModel,
        tokenizer: Tokenizer,
        device: torch.device,
        namespace_key: Optional[str] = None,
        tokenizer_kwargs: Optional[dict] = None,
        model_kwargs: Optional[dict] = None,
    ) -> None:
        if not hf_available:
            raise ImportError("`transformers` package missing. Try `pip install dff[huggingface]`.")
        super().__init__(namespace_key=namespace_key)
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.tokenizer_kwargs = tokenizer_kwargs or {"return_tensors": "pt"}
        self.model_kwargs = model_kwargs or dict()

    def transform(self, request: str) -> Iterable:
        tokenized_examples = self.tokenizer(request, **self.tokenizer_kwargs)
        output = self.model(**tokenized_examples.to(self.device), **{**self.model_kwargs, "output_hidden_states": True})
        return (
            output.hidden_states[-1][0, 0, :].detach().numpy().reshape(1, -1)
        )  # reshape for cosine similarity to be applicable

    def call_model(self, request: str) -> dict:
        tokenized_examples = self.tokenizer(request, **self.tokenizer_kwargs)
        output = self.model(
            **tokenized_examples.to(self.device), **{**self.model_kwargs, "output_hidden_states": False}
        )
        return output

    def fit(self, dataset: Dataset) -> None:
        raise NotImplementedError

    def save(self, path: str, **kwargs) -> None:
        """
        :param path: Path to saving directory.
        :param kwargs: Keyword arguments are forwarded to the 'save_pretrained' method of the underlying model.
        """
        self.model.save_pretrained(path, **kwargs)
        self.tokenizer.save_pretrained(path)

    @classmethod
    def load(cls, path: str, namespace_key: str) -> __qualname__:
        model = AutoModelForSequenceClassification.from_pretrained(path)
        tokenizer = AutoTokenizer.from_pretrained(path)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return cls(model=model, tokenizer=tokenizer, device=device, namespace_key=namespace_key)
