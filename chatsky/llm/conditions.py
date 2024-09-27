from chatsky.llm.methods import BaseMethod


def llm_condition(model_name: str, prompt: str, method: BaseMethod):
    """
    Basic function for using LLM in condition cases.

    :param model_name: Key of the model from the `Pipeline.models` dictionary.
    :param prompt: Prompt for the model to use on users input.
    :param method: Method that takes models output and returns boolean.
    """

    async def wrapped(ctx, pipeline):
        model = pipeline.models[model_name]
        return await model.condition(prompt, method)

    return wrapped
