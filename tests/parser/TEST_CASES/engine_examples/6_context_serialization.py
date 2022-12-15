from dff.core.engine.core.keywords import TRANSITIONS
from dff.core.engine.core.keywords import RESPONSE
import dff.core.engine.conditions as cnd
from dff.core.pipeline import Pipeline
toy_script = {
    'flow_start': {
        'node_start': {
            RESPONSE: response_handler,
            TRANSITIONS: {
                ('flow_start', 'node_start'): cnd.true(),
            },
        },
    },
}
pipeline = Pipeline.from_script(toy_script, start_label=('flow_start', 'node_start'), post_services=[process_response])
