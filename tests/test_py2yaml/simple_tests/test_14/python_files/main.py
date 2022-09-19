from df_engine.core.actor import Actor
from df_engine.core import keywords as kw

node = {3: "node"}

strs = strings = {
    1: {"node": {1: "node"}},
    2: {"node": {2: "node"}}
}

dicts = {1: {strs[1][node[3]][1]: {kw.RESPONSE: "hi"}}}

script = {"flow": dicts[1]}

actor = Actor(
    script,
    ("flow", strings[2][node[3]][2]),
)
