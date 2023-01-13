from dff.script import GLOBAL
from dff.script import LOCAL
from dff.script import RESPONSE
from dff.script import TRANSITIONS
from dff.script import MISC
import dff.script.labels as lbl
import dff.script.conditions as cnd
from dff.pipeline import Pipeline

toy_script = {
    'root': {
        'start': {
            RESPONSE: '',
            TRANSITIONS: {
                ('flow', 'step_0'): cnd.true(),
            },
        },
        'fallback': {
            RESPONSE: 'the end',
        },
    },
    GLOBAL: {
        MISC: {
            'var1': 'global_data',
            'var2': 'global_data',
            'var3': 'global_data',
        },
    },
    'flow': {
        LOCAL: {
            MISC: {
                'var2': 'rewrite_by_local',
                'var3': 'rewrite_by_local',
            },
        },
        'step_0': {
            MISC: {
                'var3': 'info_of_step_0',
            },
            RESPONSE: custom_response,
            TRANSITIONS: {
                lbl.forward(): cnd.true(),
            },
        },
        'step_1': {
            MISC: {
                'var3': 'info_of_step_1',
            },
            RESPONSE: custom_response,
            TRANSITIONS: {
                lbl.forward(): cnd.true(),
            },
        },
        'step_2': {
            MISC: {
                'var3': 'info_of_step_2',
            },
            RESPONSE: custom_response,
            TRANSITIONS: {
                lbl.forward(): cnd.true(),
            },
        },
        'step_3': {
            MISC: {
                'var3': 'info_of_step_3',
            },
            RESPONSE: custom_response,
            TRANSITIONS: {
                lbl.forward(): cnd.true(),
            },
        },
        'step_4': {
            MISC: {
                'var3': 'info_of_step_4',
            },
            RESPONSE: custom_response,
            TRANSITIONS: {
                'step_0': cnd.true(),
            },
        },
    },
}

pipeline = Pipeline.from_script(toy_script, start_label=('root', 'start'), fallback_label=('root', 'fallback'))
