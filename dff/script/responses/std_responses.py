"""
Responses
---------------------------
Responses are one of the most important components of the dialog graph,
which determine response for each node of a dialog graph.
This is a standard set of responses.
"""
import random
from typing import List

from dff.script import Context, Actor, Message


def choice(responses: List[Message]):
    """
    Function wrapper that takes the list of responses as an input
    and returns handler which outputs a response randomly chosen from that list.

    :param responses: A list of responses for random sampling.
    """

    def choice_response_handler(ctx: Context, actor: Actor, *args, **kwargs):
        return random.choice(responses)

    return choice_response_handler
