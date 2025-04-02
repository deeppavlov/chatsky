"""
Base Model
-----------
This module defines an abstract interface for label-scoring models, :py:class:`~ExtrasBaseAPIModel`.
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
