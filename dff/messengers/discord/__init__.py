# -*- coding: utf-8 -*-

from dff.messengers.common.modules import discord
if discord is None:
    raise ImportError("discord is not installed. Run `pip install dff[discord]`")

from .interface import DiscordInterface
