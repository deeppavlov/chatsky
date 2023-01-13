from dff.script import TRANSITIONS
from dff.script import RESPONSE
from dff.script import PROCESSING
from dff.script import LOCAL
import dff.script.conditions as cnd
import re
import dff.script.labels as lbl
from functions import add_prefix

global_flow = {
    LOCAL: {
        PROCESSING: {
            2: add_prefix('l2_local'),
            3: add_prefix('l3_local'),
        },
    },
    'start_node': {
        RESPONSE: '',
        TRANSITIONS: {
            ('music_flow', 'node1'): cnd.regexp('talk about music'),
            ('greeting_flow', 'node1'): cnd.regexp('hi|hello', re.IGNORECASE),
            'fallback_node': cnd.true(),
        },
    },
    'fallback_node': {
        RESPONSE: 'Ooops',
        TRANSITIONS: {
            ('music_flow', 'node1'): cnd.regexp('talk about music'),
            ('greeting_flow', 'node1'): cnd.regexp('hi|hello', re.IGNORECASE),
            lbl.previous(): cnd.regexp('previous', re.IGNORECASE),
            lbl.repeat(): cnd.true(),
        },
    },
}
