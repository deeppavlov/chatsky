"""
Locust
------
This module provides a `PipelineUser` class which can be used inside locust to do load testing without
creating API endpoints.

Note: this method does not work with SQLAlchemy (and possibly other dbs). If testing with sql is required, use
locust with POST endpoint instead.
"""
from locust import User
from locust.env import Environment
from typing import cast, Optional, Union, Callable, Iterable
import time
from copy import deepcopy

from dff.pipeline import Pipeline
from dff.script import Message
import uuid


class IncorrectResponse(Exception):
    """An exception thrown if a response from bot is not equal to the expected one."""
    ...


class PipelineUser(User):
    """A locust user that can check a happy path."""
    abstract = True

    def check_happy_path(
        self,
        pipeline: Pipeline,
        happy_path: Iterable[tuple[Message, Optional[Union[
            Message,
            Callable[[Message], Optional[str]],
            Callable[[Message], bool]
        ]]]]
    ):
        """
        Go through a happy path inside the same context optionally confirming the return of the pipeline.

        :param pipeline:
            An pipeline instance. Should not use any databases to store contexts.
            If load testing should be conducted with the use of databases, consider using locust with POST endpoint.
        :param happy_path:
            An iterable of tuples (Message, Message | None | Callable(Message -> str | None)).
            The first element of a tuple is a message that is passed to the pipeline.
            The second element is the Message that should be returned by the pipeline or
            a function that accepts a Message and returns an error message or
            None if correctness of the output should not be asserted.
            If the second element is a function, it should return an error message if the Message returned by
            pipeline is incorrect or None if it is correct.
        :return:
        """
        user_id = str(uuid.uuid4())
        env = cast(Environment, self.environment)
        for request, response in happy_path:
            request_meta = {
                "request_type": "PIPELINE",
                "name": str(request.json()),
                "context": {},
                "exception": None,
                "start_time": time.time(),
                "response_length": 0,
                "response_time": 0,
            }
            start_perf_counter = time.perf_counter()
            try:
                pipeline_response = pipeline(deepcopy(request), user_id).last_response
                if pipeline_response is None:
                    raise IncorrectResponse(f"Pipeline response is None.")
                request_meta["response_time"] = int((time.perf_counter() - start_perf_counter) * 1000)
                request_meta["response_length"] = len(str(pipeline_response.json()))

                if response is not None:
                    if callable(response):
                        error_message = response(pipeline_response)
                        if error_message is not None:
                            raise IncorrectResponse(error_message)
                    elif pipeline_response != response:
                        raise IncorrectResponse(f"Expected: {response.json()}\nGot: {pipeline_response.json()}")
            except Exception as e:
                request_meta["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
                request_meta["response_length"] = 0
                request_meta["exception"] = e
            finally:
                env.events.request.fire(**request_meta)

            time.sleep(self.wait_time())
