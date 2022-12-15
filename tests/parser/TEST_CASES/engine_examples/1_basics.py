from dff.core.engine.core.keywords import TRANSITIONS
from dff.core.engine.core.keywords import RESPONSE
import dff.core.engine.conditions as cnd
from dff.core.pipeline import Pipeline
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
                'node2': cnd.exact_match("i'm fine, how are you?"),
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
            RESPONSE: 'bye',
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
