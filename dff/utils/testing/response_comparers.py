from typing import Any, Optional

from requests import get

from dff.script import Context, Message


def default_comparer(candidate: Message, reference: Message, _: Context) -> Optional[Any]:
    """
    The default response comparer. Literally compares two response objects.

    :param candidate: the received (candidate) response
    :param reference: the true (reference) response
    :param _: current Context (unused)
    :return: None if two responses are equal or candidate response otherwise
    """
    return None if candidate == reference else candidate


def generics_comparer(candidate: Message, reference: Message, _: Context) -> Optional[str]:
    """
    The generics response comparer. Assumes that true response is a :py:class:`~dff.script.responses.Message` instance
    and received response is a :py:class:`str` instance.
    If received response contains `ui.buttons` it compares its text representation to true response.
    If received response contains `image`, `document`, `audio` or `video`
    it compares its `attachment` text representation to true response.
    If received response contains `attachments` it compares its `attachments` text representation to true response.
    Otherwise, it compares its `text` to true response.

    :param candidate: the received (candidate) response
    :param reference: the true response
    :param _: current Context (unused)
    :return: None if two responses are equal or candidate response text otherwise
    """
    raise DeprecationWarning()
