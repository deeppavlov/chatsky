# %% [markdown]
"""
# LLM: 5. Example Selector

If you want to provide example-guided generation for your LLM
You might be interested in writing your own or using Chatskiy's example selector.
"""
# %% [markdown]
"""
## Basic example selection

In the case you don't want to create anything complex, Chatsky provides
`StaticExampleSelector` that can be added to your project seamlesly.
This object will select all examples it holds, as shown in a code sample.
You can also add an example in run-time.
"""
# %%

from chatsky.llm.example_selector import StaticExampleSelector

examples = [
    {"input": "hi", "output": "ciao"},
    {"input": "bye", "output": "arrivaderci"},
]

selector = StaticExampleSelector(examples)

selector.add_example({"input": "soccer", "output": "calcio"})

selector.select_examples({"input": "okay"})

# %% [markdown]
"""
## How are examples being stored?

Examples are stored in a special class `Example` that has two fields: input and output.
Both of these fields can be either a `string` or a `pydantic.BaseModel`.
"""
# %%
from pydantic import BaseModel, Field
from chatsky.llm.example_selector import Example


class ResponseModel(BaseModel):
    sum: float = Field(description="Sum of the numbers")
    prod: float = Field(description="Product of the numbers")


class RequestModel(BaseModel):
    operand_1: float = Field(description="The first operand")
    operand_2: float = Field(description="The second operand")

# %% [markdown]
"""
As you can see below these two ways of representing an example are equivalent in terms of what an LLM receives.
"""
# %% 
example = Example(
    input='{"operand_1":3.0,"operand_2":4.0}', 
    output='{"sum":7.0,"prod":12.0}'
)
example.to_dict()
# %%
example = Example(
    input=RequestModel(operand_1=3.0, operand_2=4.0),
    output=ResponseModel(sum=7.0, prod=12.0),
)
example.to_dict()
# %%
example = Example(
    input='{"operand_1":3.0,"operand_2":4.0}',
    output=ResponseModel(sum=7.0, prod=12.0),
)
example.to_dict()
# %%
example = Example(
    input=RequestModel(operand_1=3.0, operand_2=4.0),
    output='{"sum":7.0,"prod":12.0}',
)
example.to_dict()
# %% [markdown]
"""
## Custom Example Selectors

If you want to add custom example selection logic, you just need to

1. Inherit from `langchain_core.example_selectors.base.BaseExampleSelector`.
2. Write your own implementation of `add_example` and  `select_examples` maintaining API in 
order to have async copies of these methods.
3. Add parameter values for selection in `input_variables` if your selector is parametrized.

All three steps are shown below:
"""
# %%

import numpy as np
from pydantic import RootModel
from typing import List, Dict, Any
from langchain_core.example_selectors.base import BaseExampleSelector


class CustomExampleSelector(BaseExampleSelector, RootModel):
    """Example Selector that randomly selects examples"""

    root: List[Example]

    def add_example(self, example: Dict[str, str]) -> Any:
        self.root.append(Example.model_validate(example))

    def select_examples(self, input_variables: Dict[str, str]) -> List[dict]:
        subset = np.random.choice(
            self.root, input_variables["size"], input_variables["replace"]
        )
        return [example.to_dict() for example in subset]


# %%
examples = [
    {"input": "hi", "output": "ciao"},
    {"input": "bye", "output": "arrivaderci"},
    {"input": "soccer", "output": "calcio"},
]

selector = CustomExampleSelector(examples)

selector.select_examples({"input": "okay", "size": 2, "replace": True})

# %% [markdown]
"""
## Convert message to LangChain context format

Chatsky also supports selection of examples that are immediately cast to the LangChain message format

All you have to do is to pass your selector in `to_langchain_context` along with `input_variables`

"""


# %%
from chatsky.llm.example_selector import to_langchain_context

examples = [
    {"input": "hi", "output": "ciao"},
    {"input": "bye", "output": "arrivaderci"},
    {"input": "soccer", "output": "calcio"},
]

selector = CustomExampleSelector(examples)

await to_langchain_context(
    selector, input_variables={"input": "okay", "size": 2, "replace": True}
)
