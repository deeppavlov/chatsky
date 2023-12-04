"""
HuggingFace classifier
----------------------

This module provides an adapter interface for Hugging Face models.
Use pre-trained NLU classifiers to make the most of your conversational data.
"""

from dff.script.extras.conditions.models.huggingface import BaseHFModel

try:
    from torch.nn import Softmax

    torch_available = True
except ImportError:
    Softmax = object
    torch_available = False


class HFClassifier(BaseHFModel):
    """
    HFClassifier utilizes Hugging Face models to predict utterance labels.

    :param model: A pretrained Hugging Face format model.
    :param tokenizer: A pretrained Hugging Face tokenizer.
    :param device: Pytorch device object. The device will be used for inference and pre-training.
    :param namespace_key: Name of the namespace in framework states that the model will be using.
    :param tokenizer_kwargs: Default tokenizer arguments override.
    :param model_kwargs: Default model arguments override.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not torch_available:
            raise ImportError("`torch` missing. Try `pip install dff[huggingface].`.")
        self.softmax = Softmax(dim=1)

    def predict(self, request: str) -> dict:
        model_output = self.call_model(request)
        logits_list = self.softmax.forward(model_output.logits).squeeze(0)
        result = {}
        for idx in range(logits_list.shape[0]):
            label = self.model.config.id2label[idx]
            result[label] = logits_list[idx].item()
        return result
