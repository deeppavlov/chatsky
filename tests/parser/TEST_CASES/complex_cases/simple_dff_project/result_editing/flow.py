from dff.script.core.keywords import TRANSITIONS
from dff.script.core.keywords import RESPONSE
import dff.script.conditions as cnd
import re
import dff.script.labels.std_labels as lbl
import re

global_flow = {
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
