# -*- coding: utf-8 -*-

try:
    import discord
except ImportError:
    raise ImportError("discord is not installed. Run `pip install dff[discord]`")

from .interface import DiscordInterface
