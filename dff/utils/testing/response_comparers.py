from typing import Any, Optional

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
