"""
Responses
---------------------------
Responses are one of
the most important components of the dialog graph,
which determine response for each node of a dialog graph.
This is a standard set of engine
responses.
"""
import random
from .core.context import Context
from .core.actor import Actor


def choice(responses: list):
    """
    Function wrapper that takes the list of responses as an input,
    and returns handler which outputs a response randomly chosen from that list.

    Parameters
    ----------

    responses: list
        a list of responses for random sampling
    """

    def choice_response_handler(ctx: Context, actor: Actor, *args, **kwargs):
        return random.choice(responses)

    return choice_response_handler
