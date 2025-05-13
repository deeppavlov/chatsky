# %% [markdown]
"""
# LLM: 5. Example Selector

If you want to provide example guided deneration for your LLM
you might be interested in writing your own or using Chatskiy's example selector.
"""
# %% [markdown]
"""
## Basic example selection

In the case you don't want to create anything complex Chatsky provides
`StaticExampleSelector` that can be added to your project seemlesly.
This object will select all examples it holds as shown in a code sample.
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

selector.select_examples({"input" : "okay"})

# %% [markdown]
"""
## How examples are being stored?

Examples stored in special class `Example` that has two fields: input and output.
Both of these fields can be either a `string` or a `pydantic.BaseModel`

To help user handle nested models that tend to be tricky to process, Chatsky provides
static method `StaticExampleSelector.unpack_model()` that returns pydantic model
in JSON-like string.
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

Example(
    input='{"operand_1":3.0,"operand_2":4.0}', 
    output='{"sum":7.0,"prod":12.0}'
)

# %%
Example(
    input=RequestModel(operand_1=3.0, operand_2=4.0), 
    output=ResponseModel(sum=7.0, prod=12.0)
)

# %%
Example(
    input='{"operand_1":3.0,"operand_2":4.0}', 
    output=ResponseModel(sum=7.0, prod=12.0)
)

# %%
example = Example(
    input=RequestModel(operand_1=3.0, operand_2=4.0), 
    output='{"sum":7.0,"prod":12.0}'
)

StaticExampleSelector.unpack_model(example.input)

# %% [markdown]
"""
## Custom Example Selectors

If you want to add custom example selection logic you just need to:

1. Inherit from `langchain_core.example_selectors.base.BaseExampleSelector` and `pydantic.RootModel`
2. Write your own implemntation of `add_example` and  `select_examples` maintaining API in 
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

    '''Example Selector that randomly selects examples'''

    root: List[Example]

    def add_example(self, example: Dict[str, str]) -> Any:
        self.root.append(Example.model_validate(example))

    def select_examples(self, input_variables: Dict[str, str]) -> List[dict]:
        subset = np.random.choice(self.root, input_variables["size"], input_variables["replace"])
        return [
            {
                "input": StaticExampleSelector.unpack_model(example.input), 
                "output": StaticExampleSelector.unpack_model(example.output)
            }
            for example in subset
        ]

# %%
examples = [
    {"input": "hi", "output": "ciao"},
    {"input": "bye", "output": "arrivaderci"},
    {"input": "soccer", "output": "calcio"}
]

selector = CustomExampleSelector(examples)

selector.select_examples({"input" : "okay", "size" : 2, "replace" : True})

# %% [markdown]
"""
Conver message to Langchain context format

Chatsky also supports selection of examples that immediately casted to langchain message format

All you have to do is to pass your selector in `to_langchain_context` along with `input_variables`

"""


# %%
from chatsky.llm.example_selector import to_langchain_context

examples = [
    {"input": "hi", "output": "ciao"},
    {"input": "bye", "output": "arrivaderci"},
    {"input": "soccer", "output": "calcio"}
]

selector = CustomExampleSelector(examples)

await to_langchain_context(
    selector, 
    input_variables={"input" : "okay", "size" : 2, "replace" : True}
)
