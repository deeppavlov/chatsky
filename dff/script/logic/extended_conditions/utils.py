"""
Utils
******

This module contains helpful constants and magic variables.
"""
import re
from typing import Optional, List

from pydantic import BaseModel

STATUS_UNAVAILABLE = 503
STATUS_SUCCESS = 200

LABEL_KEY = "labels"


class DefaultTokenizer:
    def __init__(self):
        self.expression = re.compile(r"[\w']+|[^\w ]")

    def __call__(self, string: str):
        return re.findall(self.expression, string=string)


class RasaIntent(BaseModel):
    confidence: float
    name: str


class RasaEntity(BaseModel):
    start: int
    end: int
    confidence: Optional[float]
    value: str
    entity: str


class RasaResponse(BaseModel):
    text: str
    intent_ranking: Optional[List[RasaIntent]] = None
    intent: Optional[RasaIntent] = None
    entities: Optional[List[RasaEntity]] = None
