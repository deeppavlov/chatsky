from df_engine.core.actor import Actor as Act1
from df_engine.core import Actor as Act2

script = {
    1: "hey",
}

actor = Act1(script, (1,), (1,))
actor = Act2(script, (1,), (1,))
