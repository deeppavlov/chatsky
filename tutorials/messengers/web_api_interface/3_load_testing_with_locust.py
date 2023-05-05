# %% [markdown]
"""
# Web API: 3. Load testing with Locust

This tutorial shows how to use an API endpoint created in the FastAPI tutorial in load testing.

You can either run this file directly or run locust targeting this file.

You can see the result at http://127.0.0.1:8089.
At the locust config page pass http://127.0.0.1:8000 as host.
"""


# %%
import uuid
import time
import sys
from locust import FastHttpUser, task, constant, main
from dff.script import Message
from dff.utils.testing import HAPPY_PATH, is_interactive_mode


# %%
class DFFUser(FastHttpUser):
    wait_time = constant(1)

    def check_happy_path(self, happy_path):
        user_id = str(uuid.uuid4())
        for request, response in happy_path:
            with self.client.post(
                f"/chat?user_id={user_id}",
                headers={"accept": "application/json", "Content-Type": "application/json"},
                name=f"/chat?user_message={request.json()}",
                data=request.json(),
                catch_response=True,
            ) as candidate_response:
                text_response = Message.parse_obj(candidate_response.json().get("response"))
                if response is not None:
                    if callable(response):
                        error_message = response(text_response)
                        if error_message is not None:
                            candidate_response.failure(error_message)
                    elif text_response != response:
                        candidate_response.failure(
                            f"Expected: {response.json()}\nGot: {text_response.json()}"
                        )

            time.sleep(self.wait_time())

    @task(3)  # <- this task is 3 times more likely than the other
    def dialog_1(self):
        self.check_happy_path(HAPPY_PATH)

    @task
    def dialog_2(self):
        def check_first_message(msg: Message) -> str | None:
            if msg.text is None:
                return f"Message does not contain text: {msg.json()}"
            if "Hi" not in msg.text:
                return f'"Hi" is not in the response message: {msg.json()}'
            return None

        self.check_happy_path(
            [
                # a function can be used to check the return message
                (Message(text="Hi"), check_first_message),
                # a None is used if return message should not be checked
                (Message(text="i'm fine, how are you?"), None),
                # this should fail
                (Message(text="Hi"), check_first_message),
            ]
        )


# %%
if __name__ == "__main__":
    if is_interactive_mode():
        sys.argv = ["locust", "-f", __file__]
        main.main()
