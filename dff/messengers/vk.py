"""
Interface
------------
"""
from typing import Callable, Optional, Sequence, cast
from pydantic import HttpUrl
import asyncio
import aiofiles
import aiohttp

import logging
import requests
import io
import os

from dff.messengers.common import PollingMessengerInterface

from dff.script.core.message import (
    Audio,
    Document,
    Image,
    Message,
    Video,
    Link
)

from dff.script.extra_types import Poll

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def vk_api_call(method, payload={}, headers={}):
    async with aiohttp.ClientSession() as session:
        async with session.post(method) as response:
            return response.json()


def extract_vk_update(updates):
    upds = []
    for i in updates["updates"]:
        text, id = i['object']['message']['text'], i['object']['message']['from_id']
        message = Message(text=text)
        upds.append(
            message, int(id)
        )
    return upds


class VK_Poll():
    def __init__(self) -> None:
        raise NotImplementedError()


class FilesOpener(object):
    def __init__(self, paths, key_format='file{}'):
        if not isinstance(paths, list):
            paths = [paths]

        self.paths = paths
        self.key_format = key_format
        self.opened_files = []

    def __enter__(self):
        return self.open_files()

    def __exit__(self, type, value, traceback):
        self.close_files()

    def open_files(self):
        self.close_files()

        files = []

        for x, file in enumerate(self.paths):
            if hasattr(file, 'read'):
                f = file

                filename = file.name if hasattr(file, 'name') else '.jpg'
            else:
                filename = file
                if "http" in filename:
                    f = io.BytesIO(requests.get(filename).content)
                else:
                    f = open(filename, 'rb')
                self.opened_files.append(f)

            ext = filename.split('.')[-1]
            _, filename = os.path.split(filename)
            files.append((self.key_format.format(x), (filename, f)))

        return files

    def close_files(self):
        for f in self.opened_files:
            f.close()

        self.opened_files = []


class VK_Bot:
    def __init__(self, token: str, group_id: str) -> None:
        self.token = token
        self.group_id = group_id
        server_request = requests.post(f"https://api.vk.com/method/groups.getLongPollServer?group_id={self.group_id}&v=5.81&access_token={self.token}").json()
        
        if "response" not in server_request:
            raise Exception(f"Errror getting longpoll server\n{server_request}")
        
        self.server = server_request['response']['server']
        self.ts_base = int(server_request['response']['ts'])
        self.ts_current = self.ts_base
        self.server_key = server_request['response']['key']
        self.last_update_id = None
        self._last_processed_update = None
    
    def upload_attachment(
        self, peer_id, attachment, attachment_type: str
    ) -> str:
        """
        Return json object with `owner_id` and `photo_id` needed to send it
        """
        if attachment_type == "photo":
            upload_url = requests.post(
                f"https://api.vk.com/method/photos.getMessagesUploadServer?peer_id={peer_id}&group_id={self.group_id}&v=5.81&access_token={self.token}"
            ).json()
            
            if "response" not in upload_url:
                logger.error(f"Error getting upload server for image\n{upload_url}")
                raise Exception()
            
            upload_url = upload_url["response"]["upload_url"]
            attachment_path = str(attachment.source)

            logger.info(f"Uploading {attachment_path}")
            with FilesOpener(attachment_path) as photo_files:
                uploaded_photo_data = requests.post(upload_url, files=photo_files).json()

            saved_photo_data = requests.post(f"https://api.vk.com/method/photos.saveMessagesPhoto?&group_id={self.group_id}&v=5.81&access_token={self.token}&photo={uploaded_photo_data['photo']}&server={uploaded_photo_data['server']}&hash={uploaded_photo_data['hash']}").json()
            
            if "response" not in saved_photo_data:
                logger.error(f"Error saving photo\n{saved_photo_data}")
                raise Exception()
            
            return saved_photo_data["response"]
        
        elif attachment_type == "doc":
            upload_url = requests.post(
                f"https://api.vk.com/method/docs.getMessagesUploadServer?peer_id={peer_id}&group_id={self.group_id}&v=5.81&access_token={self.token}"
            ).json()
            attachment_path = str(attachment.source)
            
            if "response" not in upload_url:
                logger.error(f"Errror getting upload server for document\n{upload_url}")
                raise Exception()
            
            upload_url = upload_url["response"]["upload_url"]

            logger.info(f"Uploading {attachment_path}")
            with FilesOpener(attachment_path, key_format="file") as files:
                uploaded_photo_data = requests.post(upload_url, files=files).json()

            saved_doc_data = requests.post(f"https://api.vk.com/method/docs.save?file={uploaded_photo_data['file']}&group_id={self.group_id}&v=5.81&access_token={self.token}").json()
            
            if "response" not in saved_doc_data:
                logger.error(f"Error saving document\n{saved_doc_data}")
                raise Exception()
            
            return saved_doc_data["response"]
        
        elif attachment_type == "audio":
            upload_url = requests.post(
                f"https://api.vk.com/method/docs.getMessagesUploadServer?peer_id={peer_id}&group_id={self.group_id}&v=5.81&access_token={self.token}&type=audio_message"
            ).json()
            attachment_path = str(attachment.source)
            
            if "response" not in upload_url:
                logger.error(f"Errror getting upload server for audio\n{upload_url}")
                raise Exception()
            
            upload_url = upload_url["response"]["upload_url"]
            
            logger.info(f"Uploading {attachment_path}")
            with FilesOpener(attachment_path, key_format="file") as files:
                uploaded_photo_data = requests.post(upload_url, files=files).json()

            saved_doc_data = requests.post(f"https://api.vk.com/method/docs.save?file={uploaded_photo_data['file']}&group_id={self.group_id}&v=5.81&access_token={self.token}").json()
            
            if "response" not in saved_doc_data:
                logger.error(f"Error saving audio\n{saved_doc_data}")
                raise Exception()
            
            return saved_doc_data["response"]
        
        elif attachment_type == "video":
            raise NotImplementedError()
        
    def request(self):
        updates = requests.post(f"{self.server}?act=a_check&key={self.server_key}&ts={self.ts_current}&wait=50").json()
        self.ts_current = updates['ts']
        return updates["updates"]

    def send_message(self, response, id, attachment_list):
        if attachment_list != []:
            for attachment in attachment_list:
                data_to_send = self.upload_attachment(id, attachment["source"], attachment["type"])
                attachment_list.append(f"photo{data_to_send[0]['owner_id']}_{data_to_send[0]['id']}")
                # elif isinstance(attachment, Link):
                #     response.text += f"[{attachment.source}|{attachment.title}]"
            attachment_string = ','.join(attachment_list).strip(',')
            
            api_request = f"https://api.vk.com/method/messages.send?user_id={id}&random_id=0&message={response.text}&attachment={attachment_string}&group_id={self.group_id}&v=5.81&access_token={self.token}"
        else:
            api_request = f"https://api.vk.com/method/messages.send?user_id={id}&random_id=0&message={response.text}&v=5.81&access_token={self.token}"
        
        return requests.post(api_request).json


class PollingVKInterface(PollingMessengerInterface):
    def __init__(self, token: str, group_id: str, debug=True, test_path=None) -> None:
        super().__init__()
        self.test_path = test_path
        self.debug = debug
        self.step = -1
        if not debug:
            self.bot = VK_Bot(token, group_id)
        # else:
        #     self.bot = VK_dummy(token, group_id)


    def _request(self):
        update_list = []
        for i in self.bot.request():
            update_list.append(
                extract_vk_update((i['object']['message']['text'], i['object']['message']['from_id']))
            )
        return update_list


    def _respond(self, response):
        for resp in response:
            if response.attachments is not None:
                attachment_list = []
                for attachment in response.attachments:
                    if isinstance(attachment, Image):
                        attachment_list.append({"type": "photo", "source": attachment.source})
                    elif isinstance(attachment, Document):
                        attachment_list.append({"doc": "photo", "source": attachment.source})
                    elif isinstance(attachment, Video):
                        raise NotImplementedError()
                    elif isinstance(attachment, Audio):
                        attachment_list.append({"audio": "photo", "source": attachment.source})
                    # elif isinstance(attachment, Link):
                    #     response.text += f"[{attachment.source}|{attachment.title}]"
            self.bot.send_message(resp.last_response, resp.id, attachment_list)

        logger.info("Responded.")


    async def connect(self, callback, loop: Optional[Callable] = None, *args, **kwargs):
        await super().connect(
            callback, loop=lambda: True, timeout=1
        )