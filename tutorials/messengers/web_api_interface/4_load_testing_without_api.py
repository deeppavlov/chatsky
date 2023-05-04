# %% [markdown]
"""
# Web API: 4. Load testing with Locust without API endpoint

This tutorial shows how to do load testing without using API endpoint (from the FastAPI tutorial).

Note: this approach does not work when using SQL as context storage (and possibly under other conditions).
This approach should ideally be used only with an empty pipeline (without context storages / messenger interfaces, etc.).

You can either run this file directly or run locust targeting this file.

You can see the result at http://127.0.0.1:8089.
At the locust config page pass anything as host (or leave the field empty).
"""


# %%
import sys

from locust import task, constant, main

from dff.pipeline import Pipeline
from dff.script import Message
from dff.utils.testing import HAPPY_PATH, TOY_SCRIPT_ARGS
from dff.utils.locust_user import PipelineUser


# %%
pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS)


# %%
class DFFUser(PipelineUser):
    wait_time = constant(1)

    @task(3)  # <- this task is 3 times more likely than the other one.
    def dialog_1(self):
        self.check_happy_path(pipeline, HAPPY_PATH)

    @task
    def dialog_2(self):
        def check_first_message(msg: Message) -> str | None:
            if "Hi" not in msg.text:
                return "'Hi' is not in the response message."
            return None

        self.check_happy_path(
            pipeline,
            [
                # a function can be used to check the return message
                (Message(text="Hi"), check_first_message),
                # a None is used if return message should not be checked
                (Message(text="i'm fine, how are you?"), None),
            ]
        )


# %%
if __name__ == "__main__":
    sys.argv = ["locust", "-f", __file__]
    main.main()
