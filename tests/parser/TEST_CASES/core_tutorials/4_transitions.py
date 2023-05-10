import re
from dff.script import TRANSITIONS
from dff.script import RESPONSE
from dff.script import Message
import dff.script.conditions as cnd
import dff.script.labels as lbl
from dff.pipeline import Pipeline

toy_script = {
    'global_flow': {
        'start_node': {
            RESPONSE: Message(),
            TRANSITIONS: {
                ('music_flow', 'node1'): cnd.regexp('talk about music'),
                ('greeting_flow', 'node1'): cnd.regexp('hi|hello', re.IGNORECASE),
                'fallback_node': cnd.true(),
            },
        },
        'fallback_node': {
            RESPONSE: Message(text='Ooops'),
            TRANSITIONS: {
                ('music_flow', 'node1'): cnd.regexp('talk about music'),
                ('greeting_flow', 'node1'): cnd.regexp('hi|hello', re.IGNORECASE),
                lbl.previous(): cnd.regexp('previous', re.IGNORECASE),
                lbl.repeat(): cnd.true(),
            },
        },
    },
    'greeting_flow': {
        'node1': {
            RESPONSE: Message(text='Hi, how are you?'),
            TRANSITIONS: {
                ('global_flow', 'fallback_node', 0.1): cnd.true(),
                'node2': cnd.regexp('how are you'),
            },
        },
        'node2': {
            RESPONSE: Message(text='Good. What do you want to talk about?'),
            TRANSITIONS: {
                lbl.to_fallback(0.1): cnd.true(),
                lbl.forward(0.5): cnd.regexp('talk about'),
                ('music_flow', 'node1'): cnd.regexp('talk about music'),
                lbl.previous(): cnd.regexp('previous', re.IGNORECASE),
            },
        },
        'node3': {
            RESPONSE: Message(text='Sorry, I can not talk about that now.'),
            TRANSITIONS: {
                lbl.forward(): cnd.regexp('bye'),
            },
        },
        'node4': {
            RESPONSE: Message(text='Bye'),
            TRANSITIONS: {
                'node1': cnd.regexp('hi|hello', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
    },
    'music_flow': {
        'node1': {
            RESPONSE: Message(text='I love `System of a Down` group, would you like to talk about it?'),
            TRANSITIONS: {
                lbl.forward(): cnd.regexp('yes|yep|ok', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        'node2': {
            RESPONSE: Message(text='System of a Down is an Armenian-American heavy metal band formed in 1994.'),
            TRANSITIONS: {
                lbl.forward(): cnd.regexp('next', re.IGNORECASE),
                lbl.repeat(): cnd.regexp('repeat', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        'node3': {
            RESPONSE: Message(text='The band achieved commercial success with the release of five studio albums.'),
            TRANSITIONS: {
                lbl.forward(): cnd.regexp('next', re.IGNORECASE),
                lbl.backward(): cnd.regexp('back', re.IGNORECASE),
                lbl.repeat(): cnd.regexp('repeat', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        'node4': {
            RESPONSE: Message(text="That's all what I know."),
            TRANSITIONS: {
                greeting_flow_n2_transition: cnd.regexp('next', re.IGNORECASE),
                high_priority_node_transition('greeting_flow', 'node4'): cnd.regexp('next time', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
    },
}

pipeline = Pipeline.from_script(toy_script, start_label=('global_flow', 'start_node'), fallback_label=('global_flow', 'fallback_node'))
