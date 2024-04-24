import logging
import requests
import io
import os

from dff.messengers.vk import extract_vk_update
from dff.script.core.message import (
    Audio,
    Document,
    Image,
    Message,
    Video,
    Link
)


def generate_random_data(data_type):
    if data_type == "url":
        return "https://www.something.com/"
    elif data_type == "num":
        return 12345

class VK_dummy:
    # functionality of the VK_Bot but without actual API calls
    def __init__(self) -> None:
        self.parsed_updates = {}
        self.parsed_updates_count = 0
        self.responses = {}
        self.responses_count = 0
        
    def _request(self, updates=None):
        update_list = []
        self.parsed_updates[self.parsed_updates_count] = []
        if updates is None:
            self.bot.request()
            
        for u in updates:
            parsed_upd = extract_vk_update((u['object']['message']['text'], u['object']['message']['from_id']))
            update_list.append(
                parsed_upd
            )
            self.parsed_updates[self.parsed_updates_count].append((u, parsed_upd))
        
        self.parsed_updates_count += 1
        return update_list

    def _respond(self, response):
        self.responses[self.responses_count] = []
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
            send_request = self.bot.send_message(resp.last_response, resp.id, attachment_list)
            self.responses[self.responses_count].append((resp, send_request))
        self.responses_count += 1
    
    def get_dialogue(self):
        return self.responses
    
    def get_requests(self):
        return self.parsed_updates