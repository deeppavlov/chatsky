import sys

import pytest

from df_slots import GroupSlot, RegexpSlot, RootSlot
from df_slots.root import add_slots


def test_nesting(root: RootSlot):
    f_name = RegexpSlot(name="f_name", regexp="(?<=name )[a-z]+")
    l_name = RegexpSlot(name="l_name", regexp=".+")
    name = GroupSlot(name="name", children=[f_name, l_name])
    cat_data = GroupSlot(name="cat_data", children=[name])
    cat = GroupSlot(name="cat", children=[cat_data])
    root.children.clear()
    add_slots([cat])
    assert sorted(root.children.keys()) == [
        "cat",
        "cat/cat_data",
        "cat/cat_data/name",
        "cat/cat_data/name/f_name",
        "cat/cat_data/name/l_name",
    ]


def test_nesting_2(root: RootSlot):
    f_name = RegexpSlot(name="name", regexp=".+")
    l_name = RegexpSlot(name="name", regexp=".+")
    first = GroupSlot(name="first", children=[f_name])
    last = GroupSlot(name="last", children=[l_name])
    common = GroupSlot(name="common", children=[first, last])
    just_name = RegexpSlot(name="name", regexp=".+")
    root.children.clear()
    add_slots([just_name, common])
    assert sorted(root.children.keys()) == [
        "common",
        "common/first",
        "common/first/name",
        "common/last",
        "common/last/name",
        "name",
    ]
