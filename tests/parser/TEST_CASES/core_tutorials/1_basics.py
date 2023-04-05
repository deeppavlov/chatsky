from dff.script import TRANSITIONS
from dff.script import RESPONSE
from dff.script import Message
from dff.pipeline import Pipeline
import dff.script.conditions as cnd

toy_script = {
    'greeting_flow': {
        'start_node': {
            RESPONSE: Message(),
            TRANSITIONS: {
                'node1': cnd.exact_match(Message(text='Hi')),
            },
        },
        'node1': {
            RESPONSE: Message(text='Hi, how are you?'),
            TRANSITIONS: {
                'node2': cnd.exact_match(Message(text="I'm fine, how are you?")),
            },
        },
        'node2': {
            RESPONSE: Message(text='Good. What do you want to talk about?'),
            TRANSITIONS: {
                'node3': cnd.exact_match(Message(text="Let's talk about music.")),
            },
        },
        'node3': {
            RESPONSE: Message(text='Sorry, I can not talk about music now.'),
            TRANSITIONS: {
                'node4': cnd.exact_match(Message(text='Ok, goodbye.')),
            },
        },
        'node4': {
            RESPONSE: Message(text='Bye'),
            TRANSITIONS: {
                'node1': cnd.exact_match(Message(text='Hi')),
            },
        },
        'fallback_node': {
            RESPONSE: Message(text='Ooops'),
            TRANSITIONS: {
                'node1': cnd.exact_match(Message(text='Hi')),
            },
        },
    },
}

pipeline = Pipeline.from_script(toy_script, start_label=('greeting_flow', 'start_node'), fallback_label=('greeting_flow', 'fallback_node'))
