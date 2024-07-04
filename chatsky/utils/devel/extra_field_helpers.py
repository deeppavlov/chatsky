"""
Extra field helpers
-------------------
Helpers for managing pydantic extra fields.
"""

from typing import List

from pydantic import BaseModel


def grab_extra_fields(attachment: BaseModel, extra_fields: List[str]):
    """
    Convenience method for passing attachment extras as named arguments to API functions.
    This might be useful for making sure no typos appear in code.
    Accepts a list of extra names and makes a dictionary of extras mathing these names.

    :param attachment: attachment whose extras will be used.
    :param extra_fields: list of extras that will be used.
    """

    return {extra_field: attachment.__pydantic_extra__.get(extra_field, None) for extra_field in extra_fields}
