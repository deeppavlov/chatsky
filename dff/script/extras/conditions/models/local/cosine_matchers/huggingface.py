"""
HuggingFace Cosine Model
------------------------

This module provides an adapter interface for Huggingface models.
It leverages transformer embeddings to compute distances between utterances.
"""
from typing import Optional
from pathlib import Path

from dff.script.extras.conditions.models.huggingface import BaseHFModel, hf_available

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch

    hf_available = hf_available and True
except ImportError:
    hf_available = hf_available and False

from dff.script.extras.conditions.dataset import Dataset
from dff.script.extras.conditions.models.local.cosine_matchers.cosine_matcher_mixin import CosineMatcherMixin


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
        model: object,
        tokenizer: object,
        device: object,
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
        Save the model to the specified location.

        :param path: Path to saving directory.
        :param kwargs: Keyword arguments are forwarded to the 'save_pretrained' method of the underlying model.
        """
        saving_path = Path(path)
        self.model.save_pretrained(saving_path, **kwargs)
        self.tokenizer.save_pretrained(saving_path)
        with (saving_path / f"{self.namespace_key}.json").open("w+", encoding="utf-8") as file:
            file.write(self.dataset.model_dump_json())

    @classmethod
    def load(cls, path: str, namespace_key: str, **kwargs) -> __qualname__:
        """
        Load the model from the specified location.

        :param str: Path to saving directory.
        :param namespace_key: Name of the namespace in that the model will be using.
            Will be forwarded to the model on construction.
        """
        saving_path = Path(path)
        model = AutoModelForSequenceClassification.from_pretrained(path)
        tokenizer = AutoTokenizer.from_pretrained(path)
        dataset = Dataset.model_validate_json((saving_path / f"{namespace_key}.json").open().read())
        device = kwargs.get("device") or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return cls(model=model, tokenizer=tokenizer, device=device, dataset=dataset, namespace_key=namespace_key)
