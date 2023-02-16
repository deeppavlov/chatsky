# -*- coding: utf-8 -*-
# flake8: noqa: F401


__author__ = "Denis Kuznetsov"
__email__ = "kuznetsov.den.p@gmail.com"
__version__ = "0.2.1"


import nest_asyncio
import asyncio

loop = asyncio.get_event_loop_policy().new_event_loop()
nest_asyncio.apply(loop)
