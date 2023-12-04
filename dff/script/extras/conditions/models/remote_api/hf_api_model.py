"""
HuggingFace API Model
---------------------------

This module provides the :py:class:`~HFAPIModel` class that allows you
to use remotely hosted HuggingFace models via the HuggingFace inference API.
"""
import time
import json
import asyncio
from typing import Optional
from urllib.parse import urljoin
from http import HTTPStatus


try:
    import requests
    import httpx

    hf_api_available = True
except ImportError:
    hf_api_available = False

from dff.script.extras.conditions.models.base_model import ExtrasBaseModel
from dff.script.extras.conditions.models.remote_api.async_mixin import AsyncMixin


class AbstractHFAPIModel(ExtrasBaseModel):
    """
    Abstract class for an HF API annotator.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        namespace_key: Optional[str] = None,
        *,
        retries: int = 60,
        base_url: str = "https://api-inference.huggingface.co/models/",
        headers: Optional[dict] = None,
    ) -> None:
        super().__init__(namespace_key=namespace_key)
        self.api_key = api_key
        self.model = model
        self.headers = (
            headers if headers else {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
        )
        self.retries = retries
        self.url = urljoin(base_url, model)
        test_response = requests.get(self.url, headers=self.headers)  # assert that the model exists
        if not test_response.status_code == HTTPStatus.OK:
            raise requests.HTTPError(test_response.text)


class HFAPIModel(AbstractHFAPIModel):
    """
    This class implements a synchronous connection to the Hugging Face inference API for dialog annotation.
    Obtain an API token from Hugging Face to gain full access to hosted models.
    Note, that the service can fail, if you exceed the usage limits determined by your
    subscription type.

    :param model: Hosted model name, e. g. 'bert-base-uncased', etc.
    :param api_key: Huggingface inference API token.
    :param namespace_key: Name of the namespace in framework states that the model will be using.
    :param base_url: Base URL address of the inference API.
        Can be adjusted to use self-hosted models.
    :param retries: Number of retries in case of request failure.
    :param headers: A dictionary that overrides a standard set of headers.
    """

    def predict(self, request: str) -> dict:
        retries = 0
        while retries < self.retries:
            retries += 1
            response: requests.Response = requests.post(self.url, headers=self.headers, data=json.dumps(request))
            if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:  # Wait for model to warm up
                time.sleep(1)
            elif response.status_code == HTTPStatus.OK:
                break
            else:
                raise requests.HTTPError(str(response.status_code) + " " + response.text)

        json_response = response.json()
        result = {}
        for label_score_pair in json_response[0]:
            result.update({label_score_pair["label"]: label_score_pair["score"]})
        return result


class AsyncHFAPIModel(AsyncMixin, AbstractHFAPIModel):
    """
    This class implements an asynchronous connection to the Hugging Face API for dialog annotation.
    Obtain an API token from Hugging Face to gain full access to hosted models.
    Note, that the service can fail, if you exceed the usage limits determined by your
    subscription type.

    :param model: Hosted model name, e. g. 'bert-base-uncased', etc.
    :param api_key: Huggingface inference API token.
    :param namespace_key: Name of the namespace in framework states that the model will be using.
    :param base_url: Base URL address of the inference API.
        Can be adjusted to use self-hosted models.
    :param retries: Number of retries in case of request failure.
    :param headers: A dictionary that overrides a standard set of headers.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        namespace_key: Optional[str] = None,
        *,
        retries: int = 60,
        headers: Optional[dict] = None,
    ) -> None:
        if not hf_api_available:
            raise ImportError("`httpx` package missing. Try `pip install dff[httpx]`")
        super().__init__(model, api_key, namespace_key, retries=retries, headers=headers)

    async def predict(self, request: str) -> dict:
        client = httpx.AsyncClient()
        retries = 0
        while retries < self.retries:
            retries += 1
            response = await client.post(self.url, headers=self.headers, data=json.dumps(request))
            if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:  # Wait for model to warm up
                await asyncio.sleep(1)
            elif response.status_code == HTTPStatus.OK:
                break
            else:
                raise httpx.HTTPStatusError(str(response.status_code) + " " + response.text)

        json_response = response.json()
        result = {}
        for label_score_pair in json_response[0]:
            result.update({label_score_pair["label"]: label_score_pair["score"]})

        await client.aclose()
        return result
