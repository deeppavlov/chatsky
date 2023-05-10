from dff.script import TRANSITIONS
from dff.script import RESPONSE
from dff.script import Message
import dff.script.responses as rsp
import dff.script.conditions as cnd
from dff.pipeline import Pipeline

toy_script = {
    'greeting_flow': {
        'start_node': {
            RESPONSE: Message(),
            TRANSITIONS: {
                'node1': cnd.exact_match(Message(text='Hi')),
            },
        },
        'node1': {
            RESPONSE: rsp.choice([Message(text='Hi, what is up?'), Message(text='Hello, how are you?')]),
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
            RESPONSE: cannot_talk_about_topic_response,
            TRANSITIONS: {
                'node4': cnd.exact_match(Message(text='Ok, goodbye.')),
            },
        },
        'node4': {
            RESPONSE: upper_case_response(Message(text='bye')),
            TRANSITIONS: {
                'node1': cnd.exact_match(Message(text='Hi')),
            },
        },
        'fallback_node': {
            RESPONSE: fallback_trace_response,
            TRANSITIONS: {
                'node1': cnd.exact_match(Message(text='Hi')),
            },
        },
    },
}

pipeline = Pipeline.from_script(toy_script, start_label=('greeting_flow', 'start_node'), fallback_label=('greeting_flow', 'fallback_node'))
