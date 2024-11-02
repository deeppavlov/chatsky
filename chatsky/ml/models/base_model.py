"""
Base Model
-----------
This module defines an abstract interface for label-scoring models, :py:class:`~ExtrasBaseModel`.
When defining custom label-scoring models, always inherit from this class.
"""

from copy import copy
from abc import ABC, abstractmethod

from chatsky import Context

import uuid


class ExtrasBaseAPIModel(ABC):
    """
    Base class for label-scoring models running on remote server and accessed via API.
    Predicted scores for labels are stored in :py:class:`~chatsky.script.Context.framework_data`.
    """

    def __init__(self) -> None:
        self.model_id = uuid.uuid4()

    def __deepcopy__(self, *args, **kwargs):
        return copy(self)

    @abstractmethod
    async def predict(self, request: str) -> dict:
        """
        Predict the probability of one or several classes.

        :param request: Target request string.
        """
        raise NotImplementedError

    async def transform(self, request: str):
        """
        Get a numeric representation of the input data.

        :param request: Target request string.
        """
        raise NotImplementedError

    async def __call__(self, ctx: Context):
        """
        Saves the retrieved labels to a subspace inside the `framework_states` field of the context.
        Creates the missing namespaces, if necessary.
        """

        if ctx.last_request and ctx.last_request.text:
            labels: dict = await self.predict(ctx.last_request.text)
        else:
            labels = dict()

        ctx.framework_data.models_labels[self.model_id] = labels

        return ctx

    async def save(self, path: str, **kwargs) -> None:
        """
        Save the model to a specified location.

        :param path: string-formatted path. If tokenizer state
            needs to be saved, the path is used as the base.
        """
        raise NotImplementedError

    @classmethod
    async def load(cls, path: str, namespace_key: str):
        """
        Load a model from the specified location and instantiate the model.

        :param str: Path to saving directory.
        :param namespace_key: Name of the namespace in that the model will be using.
            Will be forwarded to the model on construction.
        """
        raise NotImplementedError
