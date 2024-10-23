"""
Utils
------

This module contains helpful constants, magic variables and types that help parse API responses.
"""
import re
from typing import Optional, List

from pydantic import BaseModel

LABEL_KEY = "labels"


class DefaultTokenizer:
    """
    This class is used as a default tokenizer for integration with
    models that do not provide their own tokenizer. It uses a compiled
    regular expression that matches words and punctuation marks.
    """

    def __init__(self):
        self.expression = re.compile(r"[\w']+|[^\w ]")

    def __call__(self, string: str):
        return re.findall(self.expression, string=string)


class RasaIntent(BaseModel):
    """Class for integration with Rasa NLU server HTTP API."""

    confidence: float
    name: str


class RasaEntity(BaseModel):
    """Class for integration with Rasa NLU server HTTP API."""

    start: int
    end: int
    confidence: Optional[float]
    value: str
    entity: str


class RasaResponse(BaseModel):
    """Class for integration with Rasa NLU server HTTP API."""

    text: str
    intent_ranking: Optional[List[RasaIntent]] = None
    intent: Optional[RasaIntent] = None
    entities: Optional[List[RasaEntity]] = None
