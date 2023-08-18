"""
Basic Config
------------
This module contains basic benchmark configurations.

It defines a simple configurations class (:py:class:`~.BasicBenchmarkConfig`)
as well as a set of configurations that covers different dialogs a user might have and some edge-cases
(:py:data:`~.basic_configurations`).
"""
from typing import Tuple, Optional
import string
import random

from humanize import naturalsize
from pympler import asizeof

from dff.script import Message, Context
from dff.utils.db_benchmark.benchmark import BenchmarkConfig


def get_dict(dimensions: Tuple[int, ...]):
    """
    Return misc dictionary build in `dimensions` dimensions.

    :param dimensions:
        Dimensions of the dictionary.
        Each element of the dimensions tuple is the number of keys on the corresponding level of the dictionary.
        The last element of the dimensions tuple is the length of the string values of the dict.

        e.g. dimensions=(1, 2) returns a dictionary with 1 key that points to a string of len 2.
        whereas dimensions=(1, 2, 3) returns a dictionary with 1 key that points to a dictionary
        with 2 keys each of which points to a string of len 3.

        So, the len of dimensions is the depth of the dictionary, while its values are
        the width of the dictionary at each level.
    """

    def _get_dict(dimensions: Tuple[int, ...]):
        if len(dimensions) < 2:
            # get a random string of length dimensions[0]
            return "".join(random.choice(string.printable) for _ in range(dimensions[0]))
        return {str(i): _get_dict(dimensions[1:]) for i in range(dimensions[0])}

    if len(dimensions) > 1:
        return _get_dict(dimensions)
    elif len(dimensions) == 1:
        return _get_dict((dimensions[0], 0))
    else:
        return _get_dict((0, 0))


def get_message(message_dimensions: Tuple[int, ...]):
    """
    Return message with a non-empty misc field.

    :param message_dimensions: Dimensions of the misc field of the message. See :py:func:`~.get_dict`.
    """
    return Message(misc=get_dict(message_dimensions))


def get_context(
    dialog_len: int,
    message_dimensions: Tuple[int, ...],
    misc_dimensions: Tuple[int, ...],
) -> Context:
    """
    Return context with a non-empty misc, labels, requests, responses fields.

    :param dialog_len: Number of labels, requests and responses.
    :param message_dimensions:
        A parameter used to generate messages for requests and responses. See :py:func:`~.get_message`.
    :param misc_dimensions:
        A parameter used to generate misc field. See :py:func:`~.get_dict`.
    """
    return Context(
        labels={i: (f"flow_{i}", f"node_{i}") for i in range(dialog_len)},
        requests={i: get_message(message_dimensions) for i in range(dialog_len)},
        responses={i: get_message(message_dimensions) for i in range(dialog_len)},
        misc=get_dict(misc_dimensions),
    )


class BasicBenchmarkConfig(BenchmarkConfig, frozen=True):
    """
    A simple benchmark configuration that generates contexts using two parameters:

    - `message_dimensions` -- to configure the way messages are generated.
    - `misc_dimensions` -- to configure size of context's misc field.

    Dialog length is configured using `from_dialog_len`, `to_dialog_len`, `step_dialog_len`.
    """

    context_num: int = 30
    """
    Number of times the contexts will be benchmarked.
    Increasing this number decreases standard error of the mean for benchmarked data.
    """
    from_dialog_len: int = 300
    """Starting dialog len of a context."""
    to_dialog_len: int = 311
    """
    Final dialog len of a context.
    :py:meth:`~.BasicBenchmarkConfig.context_updater` will return contexts
    until their dialog len is less then `to_dialog_len`.
    """
    step_dialog_len: int = 1
    """
    Increment step for dialog len.
    :py:meth:`~.BasicBenchmarkConfig.context_updater` will return contexts
    increasing dialog len by `step_dialog_len`.
    """
    message_dimensions: Tuple[int, ...] = (10, 10)
    """
    Dimensions of misc dictionaries inside messages.
    See :py:func:`~.get_message`.
    """
    misc_dimensions: Tuple[int, ...] = (10, 10)
    """
    Dimensions of misc dictionary.
    See :py:func:`~.get_dict`.
    """

    def get_context(self) -> Context:
        """
        Return context with `from_dialog_len`, `message_dimensions`, `misc_dimensions`.

        Wraps :py:func:`~.get_context`.
        """
        return get_context(self.from_dialog_len, self.message_dimensions, self.misc_dimensions)

    def info(self):
        """
        Return fields of this instance and sizes of objects defined by this config.

        :return:
            A dictionary with two keys.
            Key "params" stores fields of this configuration.
            Key "sizes" stores string representation of following values:

                - "starting_context_size" -- size of a context with `from_dialog_len`.
                - "final_context_size" -- size of a context with `to_dialog_len`.
                  A context of this size will never actually be benchmarked.
                - "misc_size" -- size of a misc field of a context.
                - "message_size" -- size of a misc field of a message.
        """
        return {
            "params": self.model_dump(),
            "sizes": {
                "starting_context_size": naturalsize(asizeof.asizeof(self.get_context()), gnu=True),
                "final_context_size": naturalsize(
                    asizeof.asizeof(get_context(self.to_dialog_len, self.message_dimensions, self.misc_dimensions)),
                    gnu=True,
                ),
                "misc_size": naturalsize(asizeof.asizeof(get_dict(self.misc_dimensions)), gnu=True),
                "message_size": naturalsize(asizeof.asizeof(get_message(self.message_dimensions)), gnu=True),
            },
        }

    def context_updater(self, context: Context) -> Optional[Context]:
        """
        Update context to have `step_dialog_len` more labels, requests and responses,
        unless such dialog len would be equal to `to_dialog_len` or exceed than it,
        in which case None is returned.
        """
        start_len = len(context.labels)
        if start_len + self.step_dialog_len < self.to_dialog_len:
            for i in range(start_len, start_len + self.step_dialog_len):
                context.add_label((f"flow_{i}", f"node_{i}"))
                context.add_request(get_message(self.message_dimensions))
                context.add_response(get_message(self.message_dimensions))
            return context
        else:
            return None


basic_configurations = {
    "large-misc": BasicBenchmarkConfig(
        from_dialog_len=1,
        to_dialog_len=50,
        message_dimensions=(3, 5, 6, 5, 3),
        misc_dimensions=(2, 4, 3, 8, 100),
    ),
    "short-messages": BasicBenchmarkConfig(
        from_dialog_len=500,
        to_dialog_len=550,
        message_dimensions=(2, 30),
        misc_dimensions=(0, 0),
    ),
    "default": BasicBenchmarkConfig(),
    "large-misc--long-dialog": BasicBenchmarkConfig(
        from_dialog_len=500,
        to_dialog_len=550,
        message_dimensions=(3, 5, 6, 5, 3),
        misc_dimensions=(2, 4, 3, 8, 100),
    ),
    "very-long-dialog-len": BasicBenchmarkConfig(
        context_num=10,
        from_dialog_len=10000,
        to_dialog_len=10050,
    ),
    "very-long-message-len": BasicBenchmarkConfig(
        context_num=10,
        from_dialog_len=1,
        to_dialog_len=3,
        message_dimensions=(10000, 1),
    ),
    "very-long-misc-len": BasicBenchmarkConfig(
        context_num=10,
        from_dialog_len=1,
        to_dialog_len=3,
        misc_dimensions=(10000, 1),
    ),
}
"""
Configuration that covers many dialog cases (as well as some edge-cases).

:meta hide-value:
"""
