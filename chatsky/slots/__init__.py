# -*- coding: utf-8 -*-
# flake8: noqa: F401

from dff.slots.slots import GroupSlot, ValueSlot, RegexpSlot, FunctionSlot
from dff.slots.conditions import slots_extracted
from dff.slots.processing import extract, extract_all, unset, unset_all, fill_template
from dff.slots.response import filled_template
