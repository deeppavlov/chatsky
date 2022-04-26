"""
Keywords
---------------------------
The keywords are described here, they are used to define the dialog graph.
"""
from enum import Enum, auto


class Keywords(Enum):
    """
    Keywords used to define the dialog script (:py:class:`~df_engine.core.script.Script`).
    The data type `dict` is used while describing the scenario.
    `Enums` of this class are used as keys in this `dict`.
    Different keys correspond to the different value types aimed at different purposes.

    Enums:

    GLOBAL : Enum(auto)
        keyword is used to define a global node.
        The value that corresponds to this key has the `dict` type with keywords:
        `{TRANSITIONS:..., RESPONSE:..., PROCESSING:..., MISC:...}`
        There can only be one global node in a script (:py:class:`~df_engine.core.script.Script`).

        The global node is defined at the flow level as opposed to regular nodes.
        This node allows to define default global values for all nodes.

    LOCAL : Enum(auto)
        the keyword that defines the local node.
        The value that corresponds to this key has the `dict` type with keywords:
        `{TRANSITIONS:..., RESPONSE:..., PROCESSING:..., MISC:...}`
        The local node is defined in the same way as all other nodes in the flow of this node.
        It also allows to redefine default values for all nodes in this node's flow.

    TRANSITIONS : Enum(auto)
        the keyword that defines possible transitions from node.
        The value that corresponds to the `TRANSITIONS` key has the `dict` type.
        Every key-value pair describes the transition node and the condition:
        `{label_to_transition_0: condition_for_transition_0, ...,  label_to_transition_N: condition_for_transition_N}`
        `label_to_transition_i` - depends node the actor transitions to, in case of
        `condition_for_transition_i`==`True`.

    RESPONSE : Enum(auto)
        the keyword that defines the result which is returned to the user after getting to the node.
        Value that corresponds to the `RESPONSE` key can have any data type.

    PROCESSING : Enum(auto)
        the keyword that defines preprocessing, that is being called before the response generation.
        The value that corresponds to the `PROCESSING` key, must have the `dict` type:
        `{"PROC_0": proc_func_0, ..., "PROC_N": proc_func_N}`
        `"PROC_i"` is an arbitrary name of the preprocessing stage in the pipeline.
        The order of `proc_func_i` calls is defined by the order of defining of `dict` preprocessing/

    MISC : Enum(auto)
        the keyword that defines `dict` containing extra data,
        which were not aimed to be used in the standard functions of `DFE`.
        Value corresponding to the `MISC` key must have `dict` type:
        `{"VAR_KEY_0": VAR_VALUE_0, ..., "VAR_KEY_N": VAR_VALUE_N}`
        `"VAR_KEY_0"` - is an arbitrary name of the value which is saved into the `MISC`.

    """

    GLOBAL = auto()
    LOCAL = auto()
    TRANSITIONS = auto()
    RESPONSE = auto()
    PROCESSING = auto()
    MISC = auto()


# Redefine shortcuts
GLOBAL = Keywords.GLOBAL
LOCAL = Keywords.LOCAL
TRANSITIONS = Keywords.TRANSITIONS
RESPONSE = Keywords.RESPONSE
PROCESSING = Keywords.PROCESSING
MISC = Keywords.MISC
