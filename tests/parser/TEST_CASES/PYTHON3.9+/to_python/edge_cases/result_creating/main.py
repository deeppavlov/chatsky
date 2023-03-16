from dff.script import Actor
from dff.script import TRANSITIONS
from dff.script import MISC
from something import some_var
from .transitions import transitions
import variables

var = some_var

script = {
    'start_flow': {
        'start_node': {
            TRANSITIONS: {
                transitions['two']: len(transitions[1]) > 0 > -2 > (lambda : -5 + var)() > func(),
            },
        },
        'label': {
            TRANSITIONS: transitions[8],
            MISC: {
                1: {
                    2: 7,
                }[{
                    3: 2,
                }[3]],
            },
        },
        'new': {
            TRANSITIONS: transitions[variables.number],
        },
    },
}

actor = Actor(script, start_label=('start_flow', 'start_node'), some_kwarg=another_func)
