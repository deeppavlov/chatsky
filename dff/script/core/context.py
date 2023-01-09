"""
Context
---------------------------
Data structure that is used for the context storage.
It provides a convenient interface for working with data:
adding data, data serialization, type checking etc.
"""
import logging
from uuid import UUID, uuid4

from typing import Any, Optional, Union, Dict, List, Set

from pydantic import BaseModel, validate_arguments, Field, validator
from .types import NodeLabel2Type, ModuleName
from .message import Message

logger = logging.getLogger(__name__)

Node = BaseModel


@validate_arguments
def sort_dict_keys(dictionary: dict) -> dict:
    """
    Sorting the keys in the `dictionary`. This needs to be done after deserialization,
    since the keys are deserialized in a random order.

    :param dictionary: Dictionary with unsorted keys.
    :return: Dictionary with sorted keys.
    """
    return {key: dictionary[key] for key in sorted(dictionary)}


@validate_arguments
def get_last_index(dictionary: dict) -> int:
    """
    Obtaining the last index from the `dictionary`. Functions returns `-1` if the `dict` is empty.

    :param dictionary: Dictionary with unsorted keys.
    :return: Last index from the `dictionary`.
    """
    indices = list(dictionary)
    return indices[-1] if indices else -1


class Context(BaseModel):
    """
    A structure that is used to store data about the context of a dialog.
    """

    class Config:
        property_set_methods = {
            "last_response": "set_last_response",
            "last_request": "set_last_request",
        }

    id: Union[UUID, int, str] = Field(default_factory=uuid4)
    """
    `id` is the unique context identifier. By default, randomly generated using `uuid4` `id` is used.
    `id` can be used to trace the user behaviour, e.g while collecting the statistical data.
    """
    labels: Dict[int, NodeLabel2Type] = {}
    """
    `labels` stores the history of all passed `labels`

        - key - `id` of the turn.
        - value - `label` on this turn.
    """
    requests: Dict[int, Message] = {}
    """
    `requests` stores the history of all `requests` received by the agent

        - key - `id` of the turn.
        - value - `request` on this turn.
    """
    responses: Dict[int, Message] = {}
    """
    `responses` stores the history of all agent `responses`

        - key - `id` of the turn.
        - value - `response` on this turn.
    """
    misc: Dict[str, Any] = {}
    """
    `misc` stores any custom data. The scripting doesn't use this dictionary by default,
    so storage of any data won't reflect on the work on the internal Dialog Flow Scripting functions.

        - key - Arbitrary data name.
        - value - Arbitrary data.
    """
    validation: bool = False
    """
    `validation` is a flag that signals that :py:class:`~dff.script.Actor`,
    while being initialized, checks the :py:class:`~dff.script.Script`.
    The functions that can give not validable data
    while being validated must use this flag to take the validation mode into account.
    Otherwise the validation will not be passed.
    """
    framework_states: Dict[ModuleName, Dict[str, Any]] = {}
    """
    `framework_states` is used for addons states or for
    :py:class:`~dff.script.Actor`'s states.
    :py:class:`~dff.script.Actor`
    records all its intermediate conditions into the `framework_states`.
    After :py:class:`~dff.script.Context` processing is finished,
    :py:class:`~dff.script.Actor` resets `framework_states` and
    returns :py:class:`~dff.script.Context`.

        - key - Temporary variable name.
        - value - Temporary variable data.
    """

    # validators
    _sort_labels = validator("labels", allow_reuse=True)(sort_dict_keys)
    _sort_requests = validator("requests", allow_reuse=True)(sort_dict_keys)
    _sort_responses = validator("responses", allow_reuse=True)(sort_dict_keys)

    @classmethod
    def cast(cls, ctx: Optional[Union["Context", dict, str]] = None, *args, **kwargs) -> "Context":
        """
        Transforms different data types to the objects of
        :py:class:`~dff.script.Context` class.
        Returns an object of :py:class:`~dff.script.Context`
        type that is initialized by the input data.

        :param ctx: Different data types, that are used to initialize object of
            :py:class:`~dff.script.Context` type.
            The empty object of :py:class:`~dff.script.Context`
            type is created if no data are given.
        :return: Object of :py:class:`~dff.script.Context`
            type that is initialized by the input data.
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
    def add_request(self, request: Message):
        """
        Adds to the context the next `request` corresponding to the next turn.
        The addition takes place in the `requests` and `new_index = last_index + 1`.

        :param request: `request` to be added to the context.
        """
        last_index = get_last_index(self.requests)
        self.requests[last_index + 1] = request

    @validate_arguments
    def add_response(self, response: Message):
        """
        Adds to the context the next `response` corresponding to the next turn.
        The addition takes place in the `responses`, and `new_index = last_index + 1`.

        :param response: `response` to be added to the context.
        """
        last_index = get_last_index(self.responses)
        self.responses[last_index + 1] = response

    @validate_arguments
    def add_label(self, label: NodeLabel2Type):
        """
        Adds to the context the next :py:const:`label <dff.script.NodeLabel2Type>`,
        corresponding to the next turn.
        The addition takes place in the `labels`, and `new_index = last_index + 1`.

        :param label: `label` that we need to add to the context.
        """
        last_index = get_last_index(self.labels)
        self.labels[last_index + 1] = label

    @validate_arguments
    def clear(
        self,
        hold_last_n_indices: int,
        field_names: Union[Set[str], List[str]] = {"requests", "responses", "labels"},
    ):
        """
        Deletes all recordings from the `requests`/`responses`/`labels` except for
        the last `hold_last_n_indices` turns.
        If `field_names` contains `misc` field, `misc` field is fully cleared.

        :param hold_last_n_indices: Number of last turns that remain under clearing.
        :param field_names: Properties of :py:class:`~dff.script.Context` we need to clear.
            Defaults to {"requests", "responses", "labels"}
        """
        field_names = field_names if isinstance(field_names, set) else set(field_names)
        if "requests" in field_names:
            for index in list(self.requests)[:-hold_last_n_indices]:
                del self.requests[index]
        if "responses" in field_names:
            for index in list(self.responses)[:-hold_last_n_indices]:
                del self.responses[index]
        if "misc" in field_names:
            self.misc.clear()
        if "labels" in field_names:
            for index in list(self.labels)[:-hold_last_n_indices]:
                del self.labels[index]
        if "framework_states" in field_names:
            self.framework_states.clear()

    @property
    def last_label(self) -> Optional[NodeLabel2Type]:
        """
        Returns the last :py:const:`~dff.script.NodeLabel2Type` of
        the :py:class:`~dff.script.Context`.
        Returns `None` if `labels` is empty.
        """
        last_index = get_last_index(self.labels)
        return self.labels.get(last_index)

    @property
    def last_response(self) -> Optional[Message]:
        """
        Returns the last `response` of the current :py:class:`~dff.script.Context`.
        Returns `None` if `responses` is empty.
        """
        last_index = get_last_index(self.responses)
        return self.responses.get(last_index)

    def set_last_response(self, response: Optional[Message]):
        """Sets the last `response` of the current :py:class:`~dff.core.engine.core.context.Context`.
        Required for use with various response wrappers.
        """
        last_index = get_last_index(self.responses)
        self.responses[last_index] = Message() if response is None else response

    @property
    def last_request(self) -> Optional[Message]:
        """
        Returns the last `request` of the current :py:class:`~dff.script.Context`.
        Returns `None if `requests` is empty.
        """
        last_index = get_last_index(self.requests)
        return self.requests.get(last_index)

    def set_last_request(self, request: Optional[Message]):
        """Sets the last `request` of the current :py:class:`~dff.core.engine.core.context.Context`.
        Required for use with various request wrappers.
        """
        last_index = get_last_index(self.requests)
        self.requests[last_index] = Message() if request is None else request

    @property
    def current_node(self) -> Optional[Node]:
        """
        Returns current :py:class:`~dff.script.Node`.
        """
        actor = self.framework_states.get("actor", {})
        node = (
            actor.get("processed_node")
            or actor.get("pre_response_processed_node")
            or actor.get("next_node")
            or actor.get("pre_transitions_processed_node")
            or actor.get("previous_node")
        )
        if node is None:
            logger.warning(
                "The `current_node` exists when an actor is running between `ActorStage.GET_PREVIOUS_NODE`"
                " and `ActorStage.FINISH_TURN`"
            )

        return node

    @validate_arguments
    def overwrite_current_node_in_processing(self, processed_node: Node):
        """
        Overwrites the current node with a processed node. This method only works in processing functions.

        :param processed_node: `node` that we need to overwrite current node.
        """
        is_processing = self.framework_states.get("actor", {}).get("processed_node")
        if is_processing:
            self.framework_states["actor"]["processed_node"] = processed_node
        else:
            logger.warning(
                f"The `{self.overwrite_current_node_in_processing.__name__}` "
                "function can only be run during processing functions."
            )

    def __setattr__(self, key, val):
        method = self.__config__.property_set_methods.get(key, None)
        if method is None:
            super().__setattr__(key, val)
        else:
            getattr(self, method)(val)


Context.update_forward_refs()
