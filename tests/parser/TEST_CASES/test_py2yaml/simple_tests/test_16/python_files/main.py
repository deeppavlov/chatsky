from dff.core.engine.core.actor import Actor
from dff.core.engine.core import keywords as kw

node = {3: "node"}

keywords_2 = {2: kw.RESPONSE}

keywords = {"rsp": keywords_2[2]}

strs = strings = {1: {"node": {1: "node"}}, 2: {"node": {2: "node"}}}

dicts = {1: {strs[1][node[3]][1]: {keywords["rsp"]: "hi"}}}

script = {"flow": dicts[1]}

actor = Actor(
    script,
    ("flow", strings[2][node[3]][2]),
)
