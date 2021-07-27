# %%

import os
import collections
import json

from context import Context
from flows import Flows


def statistic_handler(context: Context, flows: Flows, *args, **kwargs):
    print(context)
    node_label_history = list(context.node_label_history.values())
    nodes_counter = collections.Counter(node_label_history).most_common()
    transitions_counter = collections.Counter(list(zip(node_label_history, node_label_history[1:]))).most_common()
    file = open(os.getenv("STATISTIC_PATH"), "wt")
    json.dump({"nodes_counter": nodes_counter, "transitions_counter": transitions_counter}, file, indent=4)


os.environ["STATISTIC_PATH"] = "stats.json"
flows = Flows.parse_obj({"flows": {"globals": {}}})
context = Context()
for index in range(0, 30, 2):
    context.add_human_utterance(str(index), [index])
    context.add_actor_utterance(str(index + 1), [index + 1])
    context.add_node_label([f"flow_{index}", f"node_{index}"])
statistic_handler(context, flows)
