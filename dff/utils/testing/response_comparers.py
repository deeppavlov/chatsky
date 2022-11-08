from typing import Any

from dff.connectors.messenger.generics import Response
from dff.core.engine.core.script import Context


def default_comparer(candidate: Any, reference: Any, _: Context) -> bool:
    return candidate == reference


def generics_comparer(candidate: Response, reference: str, _: Context) -> bool:
    ui = candidate.ui
    if ui and ui.buttons:
        options = [f"{str(idx)}): {item.text}" for idx, item in enumerate(ui.buttons)]
        return "\n".join(["", candidate.text] + options) == reference

    attachment = candidate.image or candidate.document or candidate.audio or candidate.video
    if attachment and attachment.source:
        with open(attachment.source, "rb") as file:
            bytestr = file.read()
            return "\n".join(["", candidate.text, f"Attachment size: {len(bytestr)} bytes."]) == reference

    attachments = candidate.attachments
    if attachments:
        size = 0
        for attach in attachments.files:
            with open(attach.source, "rb") as file:
                bytestr = file.read()
                size += len(bytestr)
        return "\n".join(["", candidate.text, f"Grouped attachment size: {str(size)} bytes."]) == reference

    return candidate.text == reference
