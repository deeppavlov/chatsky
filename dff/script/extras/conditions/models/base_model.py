"""
Base Model
-----------
This module defines an abstract interface for label-scoring models, :py:class:`~ExtrasBaseModel`.
When defining custom label-scoring models, always inherit from this class.
"""
from copy import copy
from abc import ABC, abstractmethod

from dff.script import Context

from dff.script.extras.conditions.dataset import Dataset
from dff.script.extras.conditions.utils import LABEL_KEY


class ExtrasBaseModel(ABC):
    """
    Base class for label-scoring models.
    Namespace key should be declared, if you want the scores of your model
    to be stored in a separate namespace inside the :py:class:`~dff.script.Context` object.

    :param namespace_key: Name of the namespace in framework states that the model will be using.
    """

    def __init__(self, namespace_key: str = "default") -> None:
        self.namespace_key = namespace_key

    def __deepcopy__(self, *args, **kwargs):
        return copy(self)

    @abstractmethod
    def predict(self, request: str) -> dict:
        """
        Predict the probability of one or several classes.

        :param request: Target request string.
        """
        raise NotImplementedError

    def transform(self, request: str):
        """
        Get a numeric representation of the input data.

        :param request: Target request string.
        """
        raise NotImplementedError

    def fit(self, dataset: Dataset) -> None:
        """
        Reinitialize the inner model with the given data.

        :param dataset: Data formatted as required by the `Dataset` class.
        """
        raise NotImplementedError

    def __call__(self, ctx: Context, _):
        """
        Saves the retrieved labels to a subspace inside the `framework_states` field of the context.
        Creates the missing namespaces, if necessary.
        """

        if ctx.last_request and ctx.last_request.text:
            labels: dict = self.predict(ctx.last_request.text)
        else:
            labels = dict()
        if LABEL_KEY not in ctx.framework_states:
            ctx.framework_states[LABEL_KEY] = dict()

        namespace = self.namespace_key

        ctx.framework_states[LABEL_KEY][namespace] = labels

        return ctx

    def save(self, path: str, **kwargs) -> None:
        """
        Save the model to a specified location.

        :param path: string-formatted path. If tokenizer state
            needs to be saved, the path is used as the base.
        """
        raise NotImplementedError

    @classmethod
    def load(cls, path: str, namespace_key: str) -> __qualname__:
        """
        Load a model from the specified location and instantiate the model.

        :param str: Path to saving directory.
        :param namespace_key: Name of the namespace in that the model will be using.
            Will be forwarded to the model on construction.
        """
        raise NotImplementedError
