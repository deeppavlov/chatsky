from flows.start import flow
from dff.script import Actor

start_label = ('start_flow', 'start_node')

act = Actor(script={
    'start_flow': flow,
}, start_label=start_label)
