from dff.core.engine.core.keywords import TRANSITIONS
from dff.core.engine.core.keywords import RESPONSE
from dff.core.engine.core.keywords import PROCESSING
from dff.core.engine.core.keywords import GLOBAL
from dff.core.engine.core.keywords import MISC
import dff.core.engine.conditions as cnd
import dff.core.engine.labels as lbl
from dff.core.engine.core import Actor as Act
import dff.core.engine.responses as rsp
from functions import add_prefix
from flow import global_flow

global_flow_1 = global_flow

script = {
    GLOBAL: {
        TRANSITIONS: {
            ('greeting_flow', 'node1', 1.1): cnd.regexp('\\b(hi|hello)\\b', re.I),
            ('music_flow', 'node1', 1.1): cnd.regexp('talk about music'),
            lbl.to_fallback(0.1): cnd.true(),
            lbl.forward(): cnd.all([cnd.regexp('next\\b'), cnd.has_last_labels(labels=[('music_flow', i) for i in ['node2', 'node3']])]),
            lbl.repeat(0.2): cnd.all([cnd.regexp('repeat', re.I), cnd.negation(cnd.has_last_labels(flow_labels=['global_flow']))]),
        },
        PROCESSING: {
            1: add_prefix('l1_global'),
            2: add_prefix('l2_global'),
        },
        MISC: {
            'var1': 'global_data',
            'var2': 'global_data',
            'var3': 'global_data',
        },
        RESPONSE: "''",
    },
    'global_flow': global_flow_1,
    'greeting_flow': {
        'node1': {
            RESPONSE: rsp.choice(['Hi, what is up?', 'Hello, how are you?']),
            TRANSITIONS: {
                ('global_flow', 'fallback_node', 0.1): cnd.true(),
                'node2': cnd.regexp('how are you'),
            },
            MISC: {
                'var3': 'info_of_step_1',
            },
        },
        'node2': {
            RESPONSE: 'Good. What do you want to talk about?',
            TRANSITIONS: {
                lbl.to_fallback(0.1): cnd.true(),
                lbl.forward(0.5): cnd.regexp('talk about'),
                ('music_flow', 'node1'): cnd.regexp('talk about music'),
                lbl.previous(): cnd.regexp('previous', re.IGNORECASE),
            },
        },
        'node3': {
            RESPONSE: foo,
            TRANSITIONS: {
                lbl.forward(): cnd.regexp('bye'),
            },
        },
        'node4': {
            RESPONSE: bar('bye'),
            TRANSITIONS: {
                'node1': cnd.regexp('hi|hello', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
    },
    'music_flow': {
        'node1': {
            RESPONSE: 'I love `System of a Down` group, would you like to tell about it? ',
            TRANSITIONS: {
                lbl.forward(): cnd.regexp('yes|yep|ok', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        'node2': {
            RESPONSE: 'System of a Down is an Armenian-American heavy metal band formed in in 1994.',
            TRANSITIONS: {
                lbl.forward(): cnd.regexp('next', re.IGNORECASE),
                lbl.repeat(): cnd.regexp('repeat', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        'node3': {
            RESPONSE: 'The band achieved commercial success with the release of five studio albums.',
            TRANSITIONS: {
                lbl.forward(): cnd.regexp('next', re.IGNORECASE),
                lbl.backward(): cnd.regexp('back', re.IGNORECASE),
                lbl.repeat(): cnd.regexp('repeat', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        'node4': {
            RESPONSE: "That's all what I know",
            TRANSITIONS: {
                transitions.greeting_flow_n2_transition: cnd.regexp('next', re.IGNORECASE),
                transitions.high_priority_node_transition('greeting_flow', 'node4'): cnd.regexp('next time', re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
    },
}

actor = Act(fallback_label=('global_flow', 'fallback_node'), script=script, start_label=('global_flow', 'start_node'))
