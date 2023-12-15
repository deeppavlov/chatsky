"""
Forms
---------------------------
This module holds the :class:`~.Form` class that can be used to create a global form-filling policy.
"""
from typing import Optional, Callable, List, Dict, Union
from enum import Enum, auto
from random import choice
from math import inf
from collections import Counter

from dff.script import labels as lbl
from pydantic import BaseModel, Field, validate_call

from dff.script import Context
from dff.pipeline.pipeline.pipeline import Pipeline, FORM_STORAGE_KEY
from dff.script.core.types import NodeLabel3Type, NodeLabel2Type

from .handlers import get_values
from .types import root_slot
from .conditions import slot_extracted_condition


class FormState(Enum):
    INACTIVE = auto()
    ACTIVE = auto()
    COMPLETE = auto()
    FAILED = auto()


class FormPolicy(BaseModel):
    """
    This class holds a mapping between slots and nodes that are required to set them.
    To make this policy affect the dialogue and enforce transitions to required nodes,
    you should include `to_next_slot` method into `GLOBAL` `TRANSITIONS` of your :py:class:`~.Script`.
    Check out the method documentation for details.

    .. code-block::
        :caption: Sample form class usage.

        slot_1 = RegexpSlot(...)
        form_1 = Form(name=..., mapping={slot_1.name: [("flow_1", "node_1")]})

        script = {
            GLOBAL: {
                TRANSITIONS: {
                    form_1.to_next_slot(0.1): form_1.has_state(FormState.ACTIVE)
                },
                PRE_TRANSITION_PROCESSING: {
                    "extract_1": slot_procs.extract([slot_1.name])
                }
            }
            "flow_1": {
                "node_1": {
                    RESPONSE: "Some response",
                }
            }
        }

    """

    name: str
    mapping: Dict[str, List[NodeLabel2Type]] = Field(default_factory=dict)
    allowed_repeats: int = Field(default=0, gt=-1)
    node_cache: Dict[NodeLabel2Type, int] = Field(default_factory=Counter)

    def __init__(
        self, name: str, mapping: Dict[str, List[NodeLabel2Type]], *, allowed_repeats: int = 0, **data
    ) -> None:
        """
        Create a new form.

        :param name: The name of the form used for tracking the form state.
        :param mapping: A dictionary that maps slot names to nodes.
            Nodes should be described with (flow_name, node_name) tuples.
            In case one node should set multiple slots, include them in a common group slot
            and use the name of the group slot as a key.
            Since `dict` type is ordered since python 3.6, slots will be iterated over in the order
            that you pass them in.
        :param allowed_repeats: This parameter regulates, how many times a node can be revisited.
            If the limit on allowed repeats has been reached, the policy will stop to affect transitions.
        """
        super().__init__(name=name, mapping=mapping, allowed_repeats=allowed_repeats, **data)

    @validate_call
    def to_next_label(
        self, priority: Optional[float] = None, fallback_node: Optional[Union[NodeLabel2Type, NodeLabel3Type]] = None
    ) -> Callable[[Context, Pipeline], NodeLabel3Type]:
        """
        This method checks, if all slots from the form have been set and returns transitions to required nodes,
        if there remain any. Returns an always ignored transition otherwise.

        :param priority: The weight that will be assigned to the transition.
            Defaults to 1 (default priority in dff.core.engine :py:class:`~.Pipeline`).
        """

        def to_next_label_inner(ctx: Context, pipeline: Pipeline) -> NodeLabel3Type:
            current_priority = priority or pipeline.actor.label_priority
            for slot_name, node_list in self.mapping.items():
                is_set = root_slot.children[slot_name].is_set()(ctx, pipeline)
                if is_set is True:
                    continue

                filtered_node_list = [
                    node for node in node_list if self.node_cache.get(node, 0) <= self.allowed_repeats
                ]  # assert that the visit limit has not been reached for all of the nodes.

                if len(filtered_node_list) == 0:
                    _ = self.update_state(FormState.FAILED)(ctx, pipeline)
                    fallback = fallback_node if fallback_node else lbl.to_fallback(-inf)(ctx, pipeline)
                    return fallback

                chosen_node = choice(filtered_node_list)

                if not ctx.validation:
                    self.node_cache.update([chosen_node])  # update visit counts
                return (*chosen_node, current_priority)

            _ = self.update_state(FormState.COMPLETE)(ctx, pipeline)
            fallback = fallback_node if fallback_node else lbl.to_fallback(-inf)(ctx, pipeline)
            return fallback

        return to_next_label_inner

    @validate_call
    def has_state(self, state: FormState) -> Callable[[Context, Pipeline], bool]:
        """
        This method produces a dff.core.engine condition that yields `True` if the state of the form
        equals the passed :class:`~.FormState` or `False` otherwise.

        :param state: Target state to check for.
        """

        def is_active_inner(ctx: Context, pipeline: Pipeline) -> bool:
            self.update_state()(ctx, pipeline)
            true_state = ctx.framework_states.get(FORM_STORAGE_KEY, {}).get(self.name, FormState.INACTIVE)
            return true_state == state

        return is_active_inner

    @validate_call
    def update_state(self, state: Optional[FormState] = None) -> Callable[[Context, Pipeline], None]:
        """
        This method updates the form state that is stored in the context.

        It can be called in  the ``PRE_TRANSITION_PROCESSING`` section of any node
        to explicitly set its state to a specific :class:`~.FormState` value.
        The :py:meth:`~.has_state` method also calls it before every check
        ensuring that the state is up to date.

        """

        def update_inner(ctx: Context, pipeline: Pipeline) -> None:
            ctx.framework_states.setdefault(FORM_STORAGE_KEY, {})

            if state:
                ctx.framework_states[FORM_STORAGE_KEY][self.name] = state
                return

            if self.name not in ctx.framework_states[FORM_STORAGE_KEY]:
                ctx.framework_states[FORM_STORAGE_KEY][self.name] = FormState.INACTIVE
                return

            if all([slot_extracted_condition(slot)(ctx, pipeline) for slot in self.mapping.keys()]) is True:
                ctx.framework_states[FORM_STORAGE_KEY][self.name] = FormState.COMPLETE
            return

        return update_inner

    def get_values(self) -> Callable[[Context, Pipeline], List[Dict[str, Union[str, None]]]]:
        def get_values_inner(ctx: Context, pipeline: Pipeline) -> List[Dict[str, Union[str, None]]]:
            slots = list(self.mapping.keys())
            return get_values(ctx, pipeline, slots)

        return get_values_inner
