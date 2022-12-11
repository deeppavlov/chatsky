"""
Base Model
-----------

This module defines an abstract interface for label-scoring models, :py:class:`~BaseModel`.
When defining custom label-scoring models, always inherit from this class.
"""
from copy import copy
from abc import ABC, abstractmethod

from dff.core.engine.core import Context, Actor

from ..dataset import Dataset
from ..utils import LABEL_KEY


class BaseModel(ABC):
    """
    Base class for label-scoring models.
    Namespace key should be declared, if you want the scores of your model
    to be stored in a separate namespace inside the :py:class:`dff.core.engine.core.Context` object.

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
        """
        raise NotImplementedError

    def transform(self, request: str):
        """
        Get a representation of the input data.
        """
        raise NotImplementedError

    def fit(self, dataset: Dataset) -> None:
        """
        Reinitialize the inner model with the given data.
        """
        raise NotImplementedError

    def __call__(self, ctx: Context, actor: Actor):
        """
        Saves the retrieved labels to a subspace inside the `framework_states` field of the context.
        Creates the missing namespaces, if necessary.
        """
        labels: dict = self.predict(ctx.last_request) if ctx.last_request else dict()

        if LABEL_KEY not in ctx.framework_states:
            ctx.framework_states[LABEL_KEY] = dict()

        namespace = self.namespace_key

        ctx.framework_states[LABEL_KEY][namespace] = labels

        return ctx

    def save(self, path: str, **kwargs) -> None:
        """
        Save the model to a specified location.
        """
        raise NotImplementedError

    @classmethod
    def load(cls, path: str, namespace_key: str) -> __qualname__:
        """
        Load a model from the specified location and instantiate the model.
        """
        raise NotImplementedError
