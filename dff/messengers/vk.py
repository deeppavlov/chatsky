"""
Interface
------------
"""

from typing import Callable, Optional
# import asyncio
# import aiofiles
import aiohttp

import logging
import requests
import io
import os

from dff.messengers.common import PollingMessengerInterface

from dff.script.core.message import Audio, Document, Image, Message, Video, DataAttachment
from dff.script.core.context import Context as ctx

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def vk_api_call(method: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(method) as response:
            return response.json()


def extract_vk_update(updates: dict):
    upds = []
    for update in updates["updates"]:
        text, id = update["object"]["message"]["text"], update["object"]["message"]["from_id"]
        attachments = []
        attachments_list = update["object"]["message"]["attachments"]
        
        if attachments_list != []:
            for attachment in attachments_list:
                att_object = attachment[attachment["type"]]
                if attachment["type"] == "audio" or attachment["type"] == "doc":
                    attachments.append(DataAttachment(source=att_object["url"], id=str(att_object["id"])))
                elif attachment["type"] == "photo":
                    attachments.append(
                        DataAttachment(
                            source=att_object["sizes"][-1]["url"],  # last one is the highest resolution
                            id=str(att_object["id"])
                        )
                    )
                    
        message = Message(text=text, attachments=attachments)
        upds.append(message)
    # why does it nest arrays?
    return upds[0]


class FilesOpener:
    def __init__(self, paths: list, key_format="file{}") -> list[tuple[str, tuple[str, io.BytesIO]]]:
        if not isinstance(paths, list):
            paths = [paths]

        self.paths = paths
        self.key_format = key_format
        self.opened_files = []

    def __enter__(self):
        return self.open_files()

    def __exit__(self, type, value, traceback):
        self.close_files()

    def open_files(self, just_bytes=False):
        self.close_files()

        files = []

        for x, file in enumerate(self.paths):
            if hasattr(file, "read"):
                f = file

                filename = file.name if hasattr(file, "name") else ".jpg"
            else:
                filename = file
                if "http" in filename:
                    f = io.BytesIO(requests.get(filename).content)
                else:
                    f = open(filename, "rb")
                self.opened_files.append(f)

            if just_bytes:
                return f.read()
            
            ext = filename.split(".")[-1]
            _, filename = os.path.split(filename)
            files.append((self.key_format.format(x), (filename, f)))

        return files

    def close_files(self):
        for f in self.opened_files:
            f.close()

        self.opened_files = []


class VKWrapper:
    def __init__(self, token: str, group_id: str) -> None:
        self.token = token
        self.group_id = group_id
        

    def connect(self):
        server_request = self.get_longpoll_server()

        if "response" not in server_request:
            raise Exception(f"Error getting longpoll server\n{server_request}")

        self.server = server_request["response"]["server"]
        self.ts_base = int(server_request["response"]["ts"])
        self.ts_current = self.ts_base
        self.server_key = server_request["response"]["key"]
        self.last_update_id = None
        self._last_processed_update = None

    async def get_longpoll_server(self):
        return await vk_api_call(f"https://api.vk.com/method/groups.getLongPollServer?group_id={self.group_id}&v=5.81&access_token={self.token}")

    async def get_upload_server(self, data_type, peer_id):
        upload_url = await vk_api_call(
            f"https://api.vk.com/method/{data_type}.getMessagesUploadServer?peer_id={peer_id}&group_id={self.group_id}&v=5.81&access_token={self.token}"
        )

        if "response" not in upload_url:
            logger.error(f"Error getting upload server for attachment\n{upload_url}")
            raise Exception()

        return upload_url["response"]["upload_url"]

    async def save_document(self, uploaded_data, title: str=""):
        saved_data = await vk_api_call(
            f"https://api.vk.com/method/docs.save?file={uploaded_data['file']}&title={title}&group_id={self.group_id}&v=5.81&access_token={self.token}"
        )

        if "response" not in saved_data:
            logger.error(f"Error saving document\n{saved_data}")
            raise Exception()

        return saved_data["response"]
    
    async def save_photo(self, uploaded_data, caption: str=""):
        saved_data = await vk_api_call(
            f"https://api.vk.com/method/photos.saveMessagesPhoto?&group_id={self.group_id}&v=5.81&access_token={self.token}&photo={uploaded_data['photo']}&caption={caption}&server={uploaded_data['server']}&hash={uploaded_data['hash']}"
        )

        if "response" not in saved_data:
            logger.error(f"Error saving photo\n{saved_data}")
            raise Exception()

        return saved_data["response"]

    async def upload_attachment(self, peer_id, attachment, attachment_type: str) -> str:
        """
        Return json object with `owner_id` and `photo_id` needed to send it
        """
        if attachment_type == "photo":
            upload_url = self.get_upload_server("photos", peer_id)
            attachment_path = str(attachment.source)

            logger.info(f"Uploading {attachment_path}")
            with FilesOpener(attachment_path) as photo_files:
                uploaded_photo_data = requests.post(
                    upload_url, files=photo_files
                ).json()

            saved_photo_data = self.save_photo(uploaded_photo_data, caption=attachment.title)

            return saved_photo_data

        elif attachment_type == "doc" or attachment_type == "audio":
            upload_url = self.get_upload_server("docs", peer_id)
            attachment_path = str(attachment.source)

            logger.info(f"Uploading {attachment_path}")
            with FilesOpener(attachment_path, key_format="file") as files:
                uploaded_photo_data = await vk_api_call(upload_url, files=files).json()

            saved_doc_data = self.save_document(uploaded_photo_data, title=attachment.title)

            return saved_doc_data["response"]

        elif attachment_type == "video":
            raise NotImplementedError()

    async def request(self, updates=None):
        if updates is None:
            updates = await vk_api_call(
                f"{self.server}?act=a_check&key={self.server_key}&ts={self.ts_current}&wait=50"
            )
        self.ts_current = updates["ts"]
        return updates["updates"]

    async def send_message(self, response: str, id, attachment_list):
        if attachment_list != []:
            for attachment in attachment_list:
                data_to_send = self.upload_attachment(
                    id, attachment["source"], attachment["type"]
                )
                attachment_list.append(
                    f"photo{data_to_send[0]['owner_id']}_{data_to_send[0]['id']}"
                )
                # elif isinstance(attachment, Link):
                #     response.text += f"[{attachment.source}|{attachment.title}]"
            attachment_string = ",".join(attachment_list).strip(",")

            api_request = f"https://api.vk.com/method/messages.send?user_id={id}&random_id=0&message={response}&attachment={attachment_string}&group_id={self.group_id}&v=5.81&access_token={self.token}"
        else:
            api_request = f"https://api.vk.com/method/messages.send?user_id={id}&random_id=0&message={response}&v=5.81&access_token={self.token}"

        return await vk_api_call(api_request)


class PollingVKInterface(PollingMessengerInterface):
    supported_request_attachment_types = {Audio, Image, Document, Image, Document}
    supported_response_attachment_types = {Audio, Image, Document, Image, Document}
    def __init__(self, token: str, group_id: str) -> None:
        super().__init__()
        self.bot = VKWrapper(token, group_id)

    async def _request(self):
        update_list = []
        for i in self.bot.request():
            update_list.append(
                extract_vk_update(
                    (i["object"]["message"]["text"], i["object"]["message"]["from_id"])
                )
            )
        return update_list

    async def _respond(self, response: ctx):
        for resp in response:
            attachment_list = []
            if response.attachments is not None:
                attachment_list = []
                for attachment in response.attachments:
                    # add id to each attachment that is being generated in upload_attachment method
                    if isinstance(attachment, Image):
                        attachment_list.append(
                            {"type": "photo", "source": attachment.source}
                        )
                    elif isinstance(attachment, Document):
                        attachment_list.append(
                            {"doc": "photo", "source": attachment.source}
                        )
                    elif isinstance(attachment, Video):
                        raise NotImplementedError()
                    elif isinstance(attachment, Audio):
                        attachment_list.append(
                            {"audio": "photo", "source": attachment.source}
                        )
                    # elif isinstance(attachment, Link):
                    #     response.text += f"[{attachment.source}|{attachment.title}]"
            # self.bot.send_message(resp.last_response, resp.id, attachment_list)
            self.bot.send_message("resp", "id", attachment_list)
            

        logger.info("Responded.")

    
    async def populate_attachment(self, attachment: DataAttachment) -> bytes:  # pragma: no cover
        if attachment.id is not None:
            file_link = await vk_api_call(f"https://api.vk.com/method/photos.getById?photos={attachment.id}&v=5.81&access_token={self.token}")[0]["sizes"][-1]["url"]
            data = FilesOpener(file_link, key_format="file").open_files(just_bytes=True)
            return bytes(data)
        else:
            raise ValueError(f"For attachment {attachment} id is not defined!")


    async def connect(self, callback, loop: Optional[Callable] = None, *args, **kwargs):
        self.bot.connect()
        await super().connect(callback, loop=lambda: True, timeout=1)
