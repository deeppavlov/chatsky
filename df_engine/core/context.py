"""
Context
---------------------------
Data structure which is used for the context storage.
It provides a convenient interface for working with data:
adding data, data serialization, type checking etc.

"""
import logging
from uuid import UUID, uuid4

from typing import ForwardRef
from typing import Any, Optional, Union

from pydantic import BaseModel, validate_arguments, Field, validator
from .types import NodeLabel2Type

logger = logging.getLogger(__name__)

Context = ForwardRef("Context")


@validate_arguments
def sort_dict_keys(dictionary: dict) -> dict:
    """
    Sorting of keys in the `dictionary`.
    It is nesessary to do it after the deserialization: keys deserialize in a random order.
    """
    return {key: dictionary[key] for key in sorted(dictionary)}


@validate_arguments
def get_last_index(dictionary: dict) -> int:
    """
    Obtaining of the last index from the `dictionary`, functions returns `-1` if the `dict` is empty.
    """
    indexes = list(dictionary)
    return indexes[-1] if indexes else -1


class Context(BaseModel):
    """
    The structure which is used for the storage of data about the dialog context.

    Parameters
    ----------

    id : Union[UUID, int, str]
        `id` is the unique context identifier.
        By default, the `id` which is randomly generated using `uuid4` is used.
        `id` can be used to trace the user behaviour,
        e.g while collecting the statistical data.

    labels : dict[int, :py:const:`~df_engine.core.types.NodeLabel2Type`]
        `labels` stores the history of all passed `labels`:

        * key - `id` of the turn
        * value - `label` on this turn

    requests : dict[int, Any]
        `requests` stores the history of all `requests` received by the agent

        * key - `id` of the turn
        * value - `request` on this turn

    responses : dict[int, Any]
        `responses` stores the history of all agent `responses`

        * key - `id` of the turn
        * value - `response` on this turn

    misc : dict[str, Any]
        `misc` stores the arbitrary data, the engine doesn't use this dictionary by default,
        so storage of any data won't reflect on the work on the internal Dialog Flow Engine functions.

        * key - arbitrary data name
        * value - arbitrary data

    validation : bool
        `validation` is a flag that signals that :py:class:`~df_engine.core.actor.Actor`,
        while being initialized, checks the :py:class:`~df_engine.core.plot.Plot`.
        The functions that can give not validable data
        while being validated must use this flag to take the validation mode into account.
        Otherwise the validation will not be passed.

    actor_state : dict[str, Any]
        `actor_state` or `a_s` is used every time while processing the :py:class:`~df_engine.core.context.Context`.
        :py:class:`~df_engine.core.actor.Actor` records all its intermediate conditions into the `actor_state`.
        After :py:class:`~df_engine.core.context.Context` processing is finished,
        :py:class:`~df_engine.core.actor.Actor` resets `actor_state`  and
        returns :py:class:`~df_engine.core.context.Context`.

        * key - temporary variable name
        * value - temporary variable data

    """

    id: Union[UUID, int, str] = Field(default_factory=uuid4)
    labels: dict[int, NodeLabel2Type] = {}
    requests: dict[int, Any] = {}
    responses: dict[int, Any] = {}
    misc: dict[str, Any] = {}
    validation: bool = False
    actor_state: dict[str, Any] = {}

    # validators
    _sort_labels = validator("labels", allow_reuse=True)(sort_dict_keys)
    _sort_requests = validator("requests", allow_reuse=True)(sort_dict_keys)
    _sort_responses = validator("responses", allow_reuse=True)(sort_dict_keys)

    @classmethod
    def cast(cls, ctx: Union[Context, dict, str] = {}, *args, **kwargs) -> Context:
        """
        Transforms different data types to the objects of :py:class:`~df_engine.core.context.Context` class.

        Parameters
        ----------
        ctx : Union[Context, dict, str]
            Different data types, that are used to initialize object of :py:class:`~df_engine.core.context.Context`
            type. The empty object of :py:class:`~df_engine.core.context.Context` type is created if no data are given.

        Returns
        -------
        Context
            Object of :py:class:`~df_engine.core.context.Context` type that is initialized by the input data
        """
        if not ctx:
            ctx = Context(*args, **kwargs)
        elif isinstance(ctx, dict):
            ctx = Context.parse_obj(ctx)
        elif isinstance(ctx, str):
            ctx = Context.parse_raw(ctx)
        elif not issubclass(type(ctx), Context):
            raise ValueError(
                f"context expected as sub class of Context class or object of dict/str(json) type, but got {ctx}"
            )
        return ctx

    @validate_arguments
    def add_request(self, request: Any):
        """
        Adds to the context the next `request`, that is correspondent to the next turn.
        The addition is happening in the `requests`, and `new_index = last_index + 1`

        Parameters
        ----------
        request : Any
            `request` that we need to add to the context
        """
        last_index = get_last_index(self.requests)
        self.requests[last_index + 1] = request

    @validate_arguments
    def add_response(self, response: Any):
        """
        Adds to the context the next `response`, that is correspondent to the next turn.
        The addition is happening in the `responses`, and `new_index = last_index + 1`

        Parameters
        ----------
        response : Any
            `response` that we need to add to the context
        """
        last_index = get_last_index(self.responses)
        self.responses[last_index + 1] = response

    @validate_arguments
    def add_label(self, label: NodeLabel2Type):
        """
        Adds to the context the next :py:const:`label <df_engine.core.types.NodeLabel2Type>`,
        that is correspondent to the next turn.
        The addition is happening in the `labels`, and `new_index = last_index + 1`

        Parameters
        ----------
        label : :py:const:`~df_engine.core.types.NodeLabel2Type`
            `label` that we need to add to the context
        """
        last_index = get_last_index(self.labels)
        self.labels[last_index + 1] = label

    @validate_arguments
    def clear(self, hold_last_n_indexes: int, field_names: list[str] = ["requests", "responses", "labels"]):
        """
        Deletes all recordings from the `requests`/`responses`/`labels` except for
        the last N turns according to the `hold_last_n_indexes`.
        If`field_names` contains `misc` field, `misc` field is fully cleared,

        Parameters
        ----------
        hold_last_n_indexes : int
            number of last turns that remein under clearing
        field_names : list[str]
             properties of :py:class:`~df_engine.core.context.Context` we need to clear
        """
        if "requests" in field_names:
            for index in list(self.requests)[:-hold_last_n_indexes]:
                del self.requests[index]
        if "responses" in field_names:
            for index in list(self.responses)[:-hold_last_n_indexes]:
                del self.responses[index]
        if "mics" in field_names:
            self.misc.clear()
        if "labels" in field_names:
            for index in list(self.labels)[:-hold_last_n_indexes]:
                del self.labels[index]

    @property
    def last_label(self) -> Optional[NodeLabel2Type]:
        """
        Returns the last :py:const:`~df_engine.core.types.NodeLabel2Type` of
        the :py:class:`~df_engine.core.context.Context`.
        Returns `None` if `labels` is empty
        """
        last_index = get_last_index(self.labels)
        return self.labels.get(last_index)

    @property
    def last_response(self) -> Optional[Any]:
        """
        Returns the last `response` of the current :py:class:`~df_engine.core.context.Context`.
        Returns `None if `responses` is empty
        """
        last_index = get_last_index(self.responses)
        return self.responses.get(last_index)

    @property
    def last_request(self) -> Optional[Any]:
        """
        Returns the last `request` of the current :py:class:`~df_engine.core.context.Context`.
        Returns `None if `requests` is empty
        """
        last_index = get_last_index(self.requests)
        return self.requests.get(last_index)

    @property
    def a_s(self) -> dict[str, Any]:
        """
        Alias of the `actor_state`
        """
        return self.actor_state


Context.update_forward_refs()
