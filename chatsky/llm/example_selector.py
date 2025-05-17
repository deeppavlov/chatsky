"""
Example selection
-------------------
This module provides support for example guided generation.
"""
from typing import Any, Dict, List

from langchain_core.example_selectors.base import BaseExampleSelector
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages.base import BaseMessage
from pydantic import BaseModel, RootModel


class Example(BaseModel):
    """Class that holds an example"""

    input: str | BaseModel
    """:obj:`input` may be in form of a string or a custom pydantic model derived from the BaseModel"""
    output: str | BaseModel
    """:obj:`output` may be in form of a string or a custom pydantic model derived from the BaseModel"""

    @staticmethod
    def unpack_model(example_part: str | BaseModel) -> str:
        """
        Utility function that helps to handle nested pydantic models.

        :param example_part: either :obj:`input` or :obj:`output` part of example that may be a nested model.

        :return: description of a model in a JSON-like string
        """
        return str(example_part.model_dump_json()) if isinstance(example_part, BaseModel) else example_part

    def to_dict(self) -> Dict[str, str]:
        """
        This function converts example to a dict

        :return: Returns example held by the class in format {"input": str, "output": str}
            if :obj:`input`/:obj:`output` was a pydantic model, then str will be JSON-like
        """
        return {"input": self.unpack_model(self.input), "output": self.unpack_model(self.output)}


async def to_langchain_context(
    example_selector: BaseExampleSelector, input_variables: Dict[str, str]
) -> List[BaseMessage]:
    """
    Function that selects examples and returns them in the format of a list with langchain messages.

    :param example_selector: selector object that implements selection logic.
    :param input_variables:  this parameter will be passed to example_selector
         to provide a way to change its behavior in run-time.

    :return: List of Langchain message objects.

    """

    result = []
    for example in await example_selector.aselect_examples(input_variables):

        result.append(HumanMessage(content=example["input"]))
        result.append(AIMessage(content=example["output"]))

    return result


class StaticExampleSelector(BaseExampleSelector, RootModel):
    """Example selector class that selects all examples it holds in :obj:`root`"""

    root: List[Example]
    """:obj:`root` Examples that StaticExampleSelector holds"""

    def add_example(self, example: Dict[str, str]) -> Any:
        """
        Function that provides support for adding single example to :obj:`root`.

        :param example: example that will be added to the :obj:`root`.
        """
        self.root.append(Example.model_validate(example))

    def select_examples(self, input_variables: Dict[str, str]) -> List[dict]:
        """
        Function that selects all examples in the :obj:`root`.

        :param input_variables: unused parameter to mantain API (enables async version of this function).

        :return: list of examples packed in dict with format {"input": ..., "output": ...}
        """

        return [example.to_dict() for example in self.root]
