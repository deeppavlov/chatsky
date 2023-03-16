from dff.script import GLOBAL
from dff.script import RESPONSE
from dff.script import TRANSITIONS
from dff.script import PRE_RESPONSE_PROCESSING
from dff.script import PRE_TRANSITIONS_PROCESSING
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
            'proc_name_1': get_previous_node_response_for_response_processing,
        },
        PRE_TRANSITIONS_PROCESSING: {
            'proc_name_1': save_previous_node_response_to_ctx_processing,
        },
        TRANSITIONS: {
            lbl.forward(0.1): cnd.true(),
        },
    },
    'flow': {
        'step_0': {
            RESPONSE: Message(text='first'),
        },
        'step_1': {
            RESPONSE: Message(text='second'),
        },
        'step_2': {
            RESPONSE: Message(text='third'),
        },
        'step_3': {
            RESPONSE: Message(text='fourth'),
        },
        'step_4': {
            RESPONSE: Message(text='fifth'),
        },
    },
}

pipeline = Pipeline.from_script(toy_script, start_label=('root', 'start'), fallback_label=('root', 'fallback'))
