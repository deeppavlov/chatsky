from typing_extensions import Unpack
from pydantic import ConfigDict
from dff.script.core.message import Attachment


class Poll(Attachment):
    question: str = None
    is_anonymous: bool = 0
    is_multiple: bool = 0
    end_date: int = None
    owner_id: int = None
    add_answers: list = []
    photo_id: int = None
    background_id: int = None
    disable_unvote: bool = False
