# %% [markdown]
"""
# LLM: 2. Prompt Usage

Prompt engineering is crucial when working with LLMs, and Chatsky simplifies prompt management throughout your application. This tutorial demonstrates how to:

1. Position prompts effectively in conversation history
2. Create dynamic prompts with external data
3. Manage prompt hierarchy across different application flows
"""
# %pip install chatsky[llm] langchain-openai
# %%


import re
from chatsky import (
    TRANSITIONS,
    RESPONSE,
    GLOBAL,
    LOCAL,
    MISC,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    destinations as dst,
    BaseResponse,
    Context,
)
from langchain_openai import ChatOpenAI
from chatsky.core.message import Message
from chatsky.utils.testing import is_interactive_mode
from chatsky.llm import LLM_API
from chatsky.responses.llm import LLMResponse
from chatsky.llm.prompt import Prompt, PositionConfig
import os

# Initialize OpenAI API
openai_api_key = os.getenv("OPENAI_API_KEY")

# %% [markdown]
"""
## Prompt Positioning Configuration

Chatsky's `PositionConfig` controls how different prompt types are ordered in the conversation history. The default hierarchy is:

1. `system_prompt` - Core instructions for the model
2. `history` - Conversation context
3. `misc_prompt` - Additional prompts from nodes/flows
4. `call_prompt` - Direct response prompts
5. `last_request` - User's most recent input

Let's create a custom configuration to demonstrate positioning:
"""

# %%
# Custom position configuration
position_config = PositionConfig(
    system_prompt=0,   # First position
    history=1,         # Second position
    misc_prompt=2      # Third position
)

# Initialize LLM with custom configuration
model = LLM_API(
    ChatOpenAI(model="gpt-4", api_key=openai_api_key),
    system_prompt="You represent various bank departments. Respond according to your assigned role.",
    position_config=position_config,
)

# %% [markdown]
"""
## Dynamic Prompt Generation

Create sophisticated prompts that incorporate external data. This example shows a custom prompt class that fetches vacancy data:
"""

# %%
class VacancyPrompt(BaseResponse):
    """Dynamic prompt generator for HR vacancies"""
    
    async def call(self, ctx: Context) -> str:
        vacancies = await self.fetch_vacancies()
        return f"""You are a bank HR representative. 
                Provide information about current vacancies:
                Available positions: {', '.join(vacancies)}."""
    
    async def fetch_vacancies(self) -> list[str]:
        # Simulate API call
        return ["Java Developer", "Information Security Specialist"]


# %% [markdown]
"""
## Application Structure

This banking assistant demonstrates prompt hierarchy:
- Global prompts apply to all conversations
- Flow-specific prompts override global settings
- Node-specific prompts take highest priority
"""

# %%
banking_assistant = {
    GLOBAL: {
        MISC: {
            "base_prompt": "You are a bank receptionist. Provide general information about services.",
            "security_prompt": Prompt(
                message="Never disclose internal security protocols.",
                position=100  # Always appears last
            )
        }
    },
    "main_flow": {
        "entry_node": {
            TRANSITIONS: [Tr(dst="greeting_node", cnd=cnd.ExactMatch("Hi"))],
        },
        "greeting_node": {
            RESPONSE: LLMResponse(llm_model_name="bank_model", history=0),
            TRANSITIONS: [
                Tr(dst=("loans", "start"), cnd=cnd.Contains("loan")),
                Tr(dst=("hr", "start"), cnd=cnd.Contains("vacancy")),
                Tr(dst=dst.Current())
            ],
        }
    },
    "loans": {
        LOCAL: {
            MISC: {
                "role_prompt": "You are a loan specialist. Explain requirements:",
                "conditions": "15% interest, 10-year maximum term."
            }
        },
        "start": {
            RESPONSE: LLMResponse(llm_model_name="bank_model"),
            TRANSITIONS: [Tr(dst="main_flow", cnd=cnd.Contains("back"))]
        }
    },
    "hr": {
        LOCAL: {
            MISC: {
                "prompt": VacancyPrompt()  # Uses our dynamic prompt
            }
        },
        "start": {
            RESPONSE: LLMResponse(llm_model_name="bank_model"),
            TRANSITIONS: [
                Tr(dst="cook_info", cnd=cnd.Regex(r"\bcook\b", re.I)),
                Tr(dst="main_flow", cnd=cnd.Contains("back"))
            ]
        },
        "cook_info": {
            MISC: {
                "welcome_prompt": "Welcome new kitchen staff! Work hours: 9-5, benefits included."
            },
            RESPONSE: LLMResponse(llm_model_name="bank_model")
        }
    }
}

# %% [markdown]
"""
## Running the Application

Execute the pipeline with our configuration:
"""

# %%
pipeline = Pipeline(
    banking_assistant,
    start_label=("main_flow", "entry_node"),
    models={"bank_model": model}
)

if __name__ == "__main__":
    if is_interactive_mode():
        pipeline.run()  # Launch interactive chat interface