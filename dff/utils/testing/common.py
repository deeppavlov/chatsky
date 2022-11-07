import os

from typing import List, Callable
from uuid import uuid4

from dff.core.pipeline import Pipeline
from dff.utils.testing.response_comparers import default_comparer


def is_interactive_mode() -> bool:
    # os.getenv()
    ...
    
def check_happy_path(
    pipeline: Pipeline,
    happy_path: List,
    # This optional argument is used for additional processing of candidate responses and reference responces
    comparer: Callable[TODO] = default_comparer,
):
    ...


def run_interactive_mode(pipeline: Pipeline):
    ctx_id = uuid4() # Random
    while True:
        request = input(...)
        ctx = pipeline(request=request, ctx_id=ctx_id)
        ...
