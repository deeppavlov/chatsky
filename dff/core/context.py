import logging
from uuid import UUID, uuid4

from typing import ForwardRef
from typing import Any, Optional, Union

from pydantic import BaseModel, validate_arguments, Field


logger = logging.getLogger(__name__)

Context = ForwardRef("Context")


class Context(BaseModel):
    id: Union[UUID, int, str] = Field(default_factory=uuid4)
    node_label_history: dict[int, tuple[str, str]] = {}
    human_utterances: dict[int, str] = {}
    human_annotations: dict[int, Any] = {}
    actor_utterances: dict[int, str] = {}
    actor_annotations: dict[int, Any] = {}
    previous_history_index: int = -1
    current_history_index: int = -1
    shared_memory: dict[str, Any] = {}

    @classmethod
    def cast(
        cls,
        ctx: Union[Context, dict, str] = {},
        *args,
        **kwargs,
    ) -> Union[Context, dict, str]:
        if not ctx:
            ctx = Context()
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
    def add_human_utterance(
        self,
        text: str,
        annotation: Optional[Any] = None,
        current_history_index: Optional[int] = None,
    ):
        if current_history_index is None:
            self.current_history_index += 1
        else:
            self.current_history_index = current_history_index

        self.human_utterances[self.current_history_index] = text
        self.human_annotations[self.current_history_index] = annotation

    @validate_arguments
    def add_actor_utterance(self, text: str):
        self.actor_utterances[self.current_history_index] = text

    @validate_arguments
    def add_actor_annotation(self, annotation: Any):
        self.actor_annotations[self.current_history_index] = annotation

    @validate_arguments
    def add_node_label(self, node_label: tuple[str, str]):
        self.previous_history_index = self.current_history_index
        self.node_label_history[self.current_history_index] = node_label

    @validate_arguments
    def clear(self, hold_last_n_indexes: int, field_names: list[str] = ["human", "actor", "labels"]):
        if "human" in field_names:
            for index in list(self.human_utterances.keys())[:-hold_last_n_indexes]:
                del self.human_utterances[index]
            for index in list(self.human_annotations.keys())[:-hold_last_n_indexes]:
                del self.human_annotations[index]
        if "actor" in field_names:
            for index in list(self.actor_utterances.keys())[:-hold_last_n_indexes]:
                del self.actor_utterances[index]
            for index in list(self.actor_annotations.keys())[:-hold_last_n_indexes]:
                del self.actor_annotations[index]
        if "share" in field_names:
            self.shared_memory.clear()
        if "labels" in field_names:
            for index in list(self.node_label_history.keys())[:-hold_last_n_indexes]:
                del self.node_label_history[index]

    @property
    def previous_node_label(self):
        return self.node_label_history.get(self.previous_history_index)

    @property
    def current_human_annotated_utterance(self) -> tuple[str, Optional[Any]]:
        return self.human_utterances[self.current_history_index], self.human_annotations.get(self.current_history_index)

    @property
    def previous_human_annotated_utterance(self) -> tuple[str, Optional[Any]]:
        return self.human_utterances[self.previous_history_index], self.human_annotations.get(
            self.previous_history_index
        )

    @property
    def previous_actor_annotated_utterance(self) -> tuple[str, Optional[Any]]:
        return self.actor_utterances[self.previous_history_index], self.actor_annotations.get(
            self.previous_history_index
        )

    @property
    def actor_text_response(self) -> Optional[str]:
        last_utt = list(self.actor_utterances.values())[-1:]
        if last_utt:
            return last_utt[0]


Context.update_forward_refs()
