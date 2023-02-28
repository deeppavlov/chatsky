from dff.script import GLOBAL
from dff.script import LOCAL
from dff.script import RESPONSE
from dff.script import TRANSITIONS
from dff.script import PRE_RESPONSE_PROCESSING
from dff.script import Message
import dff.script.labels as lbl
import dff.script.conditions as cnd
from dff.pipeline import Pipeline

toy_script = {
    'root': {
        'start': {
            RESPONSE: Message(),
            TRANSITIONS: {
                ('flow', 'step_0'): cnd.true(),
            },
        },
        'fallback': {
            RESPONSE: Message(text='the end'),
        },
    },
    GLOBAL: {
        PRE_RESPONSE_PROCESSING: {
            'proc_name_1': add_prefix('l1_global'),
            'proc_name_2': add_prefix('l2_global'),
        },
    },
    'flow': {
        LOCAL: {
            PRE_RESPONSE_PROCESSING: {
                'proc_name_2': add_prefix('l2_local'),
                'proc_name_3': add_prefix('l3_local'),
            },
        },
        'step_0': {
            RESPONSE: Message(text='first'),
            TRANSITIONS: {
                lbl.forward(): cnd.true(),
            },
        },
        'step_1': {
            PRE_RESPONSE_PROCESSING: {
                'proc_name_1': add_prefix('l1_step_1'),
            },
            RESPONSE: Message(text='second'),
            TRANSITIONS: {
                lbl.forward(): cnd.true(),
            },
        },
        'step_2': {
            PRE_RESPONSE_PROCESSING: {
                'proc_name_2': add_prefix('l2_step_2'),
            },
            RESPONSE: Message(text='third'),
            TRANSITIONS: {
                lbl.forward(): cnd.true(),
            },
        },
        'step_3': {
            PRE_RESPONSE_PROCESSING: {
                'proc_name_3': add_prefix('l3_step_3'),
            },
            RESPONSE: Message(text='fourth'),
            TRANSITIONS: {
                lbl.forward(): cnd.true(),
            },
        },
        'step_4': {
            PRE_RESPONSE_PROCESSING: {
                'proc_name_4': add_prefix('l4_step_4'),
            },
            RESPONSE: Message(text='fifth'),
            TRANSITIONS: {
                'step_0': cnd.true(),
            },
        },
    },
}

pipeline = Pipeline.from_script(toy_script, start_label=('root', 'start'), fallback_label=('root', 'fallback'))
