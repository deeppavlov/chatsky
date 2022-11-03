"""
HuggingFace classifier
***********************

This module provides an adapter interface for Hugging Face models.
Use pre-trained NLU classifiers to make the most of your conversational data.
"""
try:
    from torch.nn import Softmax

    IMPORT_ERROR_MESSAGE = None
except ImportError as e:
    Softmax = object
    IMPORT_ERROR_MESSAGE = e.msg

from ...huggingface import BaseHFModel


class HFClassifier(BaseHFModel):
    """
    HFClassifier utilizes Hugging Face models to predict utterance labels.

    Parameters
    -----------
    model: PreTrainedModel
        A pretrained Hugging Face format model.
    tokenizer: Tokenizer
        A pretrained Hugging Face tokenizer.
    device: torch.device
        Pytorch device object. The device will be used for inference and pre-training.
    namespace_key: str
        Name of the namespace in framework states that the model will be using.
    tokenizer_kwargs: Optional[dict] = None
        Default tokenizer arguments override.
    model_kwargs: Optional[dict] = None
        Default model arguments override.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        IMPORT_ERROR_MESSAGE = globals().get("IMPORT_ERROR_MESSAGE")
        if IMPORT_ERROR_MESSAGE is not None:
            raise ImportError(IMPORT_ERROR_MESSAGE)
        self.sofmax = Softmax()

    def predict(self, request: str) -> dict:
        model_output = self.call_model(request)
        logits_list = self.sofmax.forward(model_output.logits).squeeze(0)
        result = {}
        for idx in range(logits_list.shape[0]):
            label = self.model.config.id2label[idx]
            result[label] = logits_list[idx].item()
        return result
