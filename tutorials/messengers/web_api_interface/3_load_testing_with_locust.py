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
from dff.utils.testing import HAPPY_PATH


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
                    catch_response=True
            ) as candidate_response:
                text_response = Message.parse_obj(candidate_response.json().get("response"))
                if text_response != response:
                    candidate_response.failure(f"Incorrect response: {text_response}")

            time.sleep(self.wait_time())

    @task
    def dialog_1(self):
        self.check_happy_path(HAPPY_PATH)


# %%
if __name__ == "__main__":
    sys.argv = ["locust", "-f", __file__]
    main.main()
