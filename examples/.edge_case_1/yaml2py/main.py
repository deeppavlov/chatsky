from abc import global_flow, start_label


script = {global_flow: {start_label: {1: [1, 2]}}, "global_flow": {2: [1, "2"]}}

start_label = (global_flow, start_label)

fallback_label = ("global_flow",)

from df_engine.core import Actor

actor = Actor(script, start_label, fallback_label)
