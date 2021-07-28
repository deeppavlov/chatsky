import logging
from uuid import UUID, uuid4

from typing import Any, Optional, Union

from pydantic import BaseModel, validate_arguments, Field


logger = logging.getLogger(__name__)


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
    def get_current_human_annotated_utterance(self) -> tuple[str, Optional[Any]]:
        return self.human_utterances[self.current_history_index], self.human_annotations.get(self.current_history_index)

    @validate_arguments
    def get_previous_human_annotated_utterance(self) -> tuple[str, Optional[Any]]:
        return self.human_utterances[self.previous_history_index], self.human_annotations.get(
            self.previous_history_index
        )

    @validate_arguments
    def get_previous_actor_annotated_utterance(self) -> tuple[str, Optional[Any]]:
        return self.actor_utterances[self.previous_history_index], self.actor_annotations.get(
            self.previous_history_index
        )

    @validate_arguments
    def add_actor_utterance(self, text: str, annotation: Optional[Any] = None):
        self.previous_history_index = self.current_history_index
        self.actor_utterances[self.previous_history_index] = text
        self.actor_annotations[self.previous_history_index] = annotation

    @validate_arguments
    def add_node_label(self, node_label: tuple[str, str]):
        self.node_label_history[self.current_history_index] = node_label

    @validate_arguments
    def clean(self, hold_last_n_indexes: int, fields: list[str] = ["human", "actor"]):
        if "human" in fields:
            for index in list(self.human_utterances.keys())[:-hold_last_n_indexes]:
                del self.human_utterances[index]
                del self.human_annotations[index]
        if "actor" in fields:
            for index in list(self.actor_utterances.keys())[:-hold_last_n_indexes]:
                del self.actor_utterances[index]
                del self.actor_annotations[index]
        if "share" in fields:
            self.shared_memory.clear()
        if "labels" in fields:
            for index in list(self.node_label_history.keys())[:-hold_last_n_indexes]:
                del self.node_label_history[index]
