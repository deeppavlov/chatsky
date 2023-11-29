# %% [markdown]
"""
# 8. Custom API Connector

This module demonstrates how you can write a connector for an external web API.
"""


# %%
import json

import requests
import httpx

from dff.script.extras.conditions.models.remote_api.async_mixin import (
    AsyncMixin,
)
from dff.script.extras.conditions.models.base_model import BaseModel
from dff.script.extras.conditions.utils import STATUS_SUCCESS


# %% [markdown]
"""
To create a synchronous connector to an API, we recommend you to inherit the class from `BaseModel`.
The only method that you have to override is the `predict` method.
It takes a request string and returns a {label: probability} dictionary.
In case the request has not been successful, an empty dictionary can be returned.

The same applies to asynchronous connectors,
although they should also inherit from `AsyncMixin` class
in order to make the `__call__` method asynchronous.
We use `httpx` as an asynchronous http client.
"""


# %%
class CustomAPIConnector(BaseModel):
    def __init__(self, url: str, namespace_key: str = "default") -> None:
        super().__init__(namespace_key)
        self.url = url

    def predict(self, request: str) -> dict:
        result = requests.post(self.url, data=json.dumps({"data": request}))
        if result.status_code != STATUS_SUCCESS:
            return {}
        json_response = result.json()
        return {
            label: probability for label, probability in json_response.items()
        }


# %%
class AsyncCustomAPIConnector(AsyncMixin, CustomAPIConnector):
    async def predict(self, request: str) -> dict:
        client = httpx.AsyncClient()
        result = await client.post(self.url, data=json.dumps({"data": request}))
        await client.aclose()
        if result.status_code != STATUS_SUCCESS:
            return {}
        json_response = result.json()
        return {
            label: probability for label, probability in json_response.items()
        }
