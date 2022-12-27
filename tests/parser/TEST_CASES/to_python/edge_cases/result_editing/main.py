from dff.script import Actor
from dff.script import TRANSITIONS
from dff.script import RESPONSE
from something import some_func
from something import some_var
from .transitions import transitions
import variables


def func():
    Actor.do_stuff()
    some_func(some_var)


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
        },
        'new': {
            TRANSITIONS: transitions[variables.number],
        },
    },
}


def another_func():
    do_stuff()


actor = Actor(script, start_label=('start_flow', 'start_node'), some_kwarg=another_func)


class Final:
    ...
