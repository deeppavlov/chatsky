from chatsky.llm.methods import BaseMethod
from chatsky.core import BaseCondition, Context, Pipeline


class LLMCondition(BaseCondition):
    model_name: str
    prompt: str
    method: BaseMethod
    pipeline: Pipeline
    
    async def call(self, ctx: Context) -> bool:
        """
        Basic function for using LLM in condition cases.

        :param model_name: Key of the model from the `Pipeline.models` dictionary.
        :param prompt: Prompt for the model to use on users input.
        :param method: Method that takes models output and returns boolean.
        """
        model = self.pipeline.models[self.model_name]
        return await model.condition(self.prompt, self.method)