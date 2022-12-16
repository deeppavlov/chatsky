from dff.core.engine.core.actor import Actor
from dff.core.engine.core.keywords import TRANSITIONS
from .transitions import transitions
import variables
script = {
    'start_flow': {
        'start_node': {
            TRANSITIONS: {
                transitions['two']: len(transitions[1]) > 0 > -2 > (lambda : -5)() > func(),
            },
        },
        'label': {
            TRANSITIONS: transitions[8],
        },
        'new': {
            TRANSITIONS: transitions[variables.number],
        },
    },
}
actor = Actor(script, start_label=('start_flow', 'start_node'), some_kwarg=another_func)
