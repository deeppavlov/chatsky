from typing import List

from pydantic import BaseModel


def generate_extra_fields(attachment: BaseModel, extra_fields: List[str]):
    return {extra_field: attachment.__pydantic_extra__.get(extra_field, None) for extra_field in extra_fields}
