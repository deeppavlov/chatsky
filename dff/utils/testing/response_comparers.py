from typing import Any, Optional

from requests import get

from dff.connectors.messenger.generics import Response
from dff.core.engine.core.script import Context


def default_comparer(candidate: Any, reference: Any, _: Context) -> Optional[str]:
    return None if candidate == reference else candidate


def generics_comparer(candidate: Response, reference: str, _: Context) -> Optional[str]:
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
