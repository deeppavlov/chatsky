from typing import Any, Optional

from requests import get

from dff.script import Context
from dff.script.responses import Message


def default_comparer(candidate: Any, reference: Any, _: Context) -> Optional[Any]:
    """
    The default response comparer. Literally compares two response objects.

    :param candidate: the received (candidate) response
    :param reference: the true (reference) response
    :param _: current Context (unused)
    :return: None if two responses are equal or candidate response otherwise
    """
    return None if candidate == reference else candidate


def generics_comparer(candidate: Message, reference: str, _: Context) -> Optional[str]:
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

    ui = candidate.ui
    if ui and ui.buttons:
        options = [f"{str(idx)}): {item.text}" for idx, item in enumerate(ui.buttons)]
        transformed = "\n".join(["", candidate.text] + options)
        return None if transformed == reference else transformed

    attachment = candidate.image or candidate.document or candidate.audio or candidate.video
    if attachment and attachment.source:
        attachment_size = int(get(attachment.source, stream=True).headers["Content-length"])
        transformed = "\n".join(["", candidate.text, f"Attachment size: {attachment_size} bytes."])
        return None if transformed == reference else transformed

    attachments = candidate.attachments
    if attachments:
        attachment_size = 0
        for attach in attachments.files:
            attachment_size += int(get(attach.source, stream=True).headers["Content-length"])
        transformed = "\n".join(["", candidate.text, f"Grouped attachment size: {attachment_size} bytes."])
        return None if transformed == reference else transformed

    return None if candidate.text == reference else candidate.text
