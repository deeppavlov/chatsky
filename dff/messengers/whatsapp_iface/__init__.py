# -*- coding: utf-8 -*-

try:
    import whatsapp
except ImportError:
    raise ImportError("whatsapp-python is not installed. Run `pip install dff[whatsapp]`")

from .interface import WhatsappInterface
