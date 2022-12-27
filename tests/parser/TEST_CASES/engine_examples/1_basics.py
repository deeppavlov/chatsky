from dff.script import TRANSITIONS
from dff.script import RESPONSE
from dff.pipeline import Pipeline
import dff.script.conditions as cnd

toy_script = {
    'greeting_flow': {
        'start_node': {
            RESPONSE: '',
            TRANSITIONS: {
                'node1': cnd.exact_match('Hi'),
            },
        },
        'node1': {
            RESPONSE: 'Hi, how are you?',
            TRANSITIONS: {
                'node2': cnd.exact_match("I'm fine, how are you?"),
            },
        },
        'node2': {
            RESPONSE: 'Good. What do you want to talk about?',
            TRANSITIONS: {
                'node3': cnd.exact_match("Let's talk about music."),
            },
        },
        'node3': {
            RESPONSE: 'Sorry, I can not talk about music now.',
            TRANSITIONS: {
                'node4': cnd.exact_match('Ok, goodbye.'),
            },
        },
        'node4': {
            RESPONSE: 'Bye',
            TRANSITIONS: {
                'node1': cnd.exact_match('Hi'),
            },
        },
        'fallback_node': {
            RESPONSE: 'Ooops',
            TRANSITIONS: {
                'node1': cnd.exact_match('Hi'),
            },
        },
    },
}

pipeline = Pipeline.from_script(toy_script, start_label=('greeting_flow', 'start_node'), fallback_label=('greeting_flow', 'fallback_node'))
