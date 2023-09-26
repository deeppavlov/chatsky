"""
Keywords
--------
Keywords are used to define the dialog graph, which is the structure of a conversation.
They are used to determine all nodes in the script and to assign python objects and python functions for nodes.

"""
from enum import Enum


class Keywords(str, Enum):
    """
    Keywords used to define the dialog script (:py:class:`~dff.script.Script`).
    The data type `dict` is used to describe the scenario.
    `Enums` of this class are used as keys in this `dict`.
    Different keys correspond to the different value types aimed at different purposes.

    Enums:

    GLOBAL: Enum(auto)
        This keyword is used to define a global node.
        The value that corresponds to this key has the `dict` type with keywords:

        `{TRANSITIONS:..., RESPONSE:..., PRE_RESPONSE_PROCESSING:..., MISC:...}`.
        There can be only one global node in a script :py:class:`~dff.script.Script`.
        The global node is defined at the flow level as opposed to regular nodes.
        This node allows to define default global values for all nodes.

    LOCAL: Enum(auto)
        This keyword is used to define the local node.
        The value that corresponds to this key has the `dict` type with keywords:

        `{TRANSITIONS:..., RESPONSE:..., PRE_RESPONSE_PROCESSING:..., MISC:...}`.
        The local node is defined in the same way as all other nodes in the flow of this node.
        It also allows to redefine default values for all nodes in this node's flow.

    TRANSITIONS: Enum(auto)
        This keyword defines possible transitions from node.
        The value that corresponds to the `TRANSITIONS` key has the `dict` type.
        Every key-value pair describes the transition node and the condition:

        `{label_to_transition_0: condition_for_transition_0, ..., label_to_transition_N: condition_for_transition_N}`,

        where `label_to_transition_i` is a node into which the actor make the transition in case of
        `condition_for_transition_i == True`.

    RESPONSE: Enum(auto)
        The keyword specifying the result which is returned to the user after getting to the node.
        Value corresponding to the `RESPONSE` key can have any data type.

    MISC: Enum(auto)
        The keyword specifying `dict` containing extra data,
        which were not aimed to be used in the standard functions of `DFE`.
        Value corresponding to the `MISC` key must have `dict` type:

        `{"VAR_KEY_0": VAR_VALUE_0, ..., "VAR_KEY_N": VAR_VALUE_N}`,

        where `"VAR_KEY_0"` is an arbitrary name of the value which is saved into the `MISC`.

    PRE_RESPONSE_PROCESSING: Enum(auto)
        The keyword specifying the preprocessing that is called before the response generation.
        The value that corresponds to the `PRE_RESPONSE_PROCESSING` key must have the `dict` type:

        `{"PRE_RESPONSE_PROC_0": pre_response_proc_func_0, ..., "PRE_RESPONSE_PROC_N": pre_response_proc__func_N}`,

        where `"PRE_RESPONSE_PROC_i"` is an arbitrary name of the preprocessing stage in the pipeline.
        The order of `pre_response_proc__func_i` calls is defined by the order
        in which the preprocessing `dict` is defined.

    PRE_TRANSITIONS_PROCESSING: Enum(auto)
        The keyword specifying the preprocessing that is called before the transition.
        The value that corresponds to the `PRE_TRANSITIONS_PROCESSING` key must have the `dict` type:

        `{"PRE_TRANSITIONS_PROC_0": pre_transitions_proc_func_0, ...,
        "PRE_TRANSITIONS_PROC_N": pre_transitions_proc_func_N}`,

        where `"PRE_TRANSITIONS_PROC_i"` is an arbitrary name of the preprocessing stage in the pipeline.
        The order of `pre_transitions_proc_func_i` calls is defined by the order
        in which the preprocessing `dict` is defined.

    """

    GLOBAL = "global"
    LOCAL = "local"
    TRANSITIONS = "transitions"
    RESPONSE = "response"
    MISC = "misc"
    PRE_RESPONSE_PROCESSING = "pre_response_processing"
    PRE_TRANSITIONS_PROCESSING = "pre_transitions_processing"
    PROCESSING = "pre_transitions_processing"


# Redefine shortcuts
GLOBAL = Keywords.GLOBAL
LOCAL = Keywords.LOCAL
TRANSITIONS = Keywords.TRANSITIONS
RESPONSE = Keywords.RESPONSE
MISC = Keywords.MISC
PRE_RESPONSE_PROCESSING = Keywords.PRE_RESPONSE_PROCESSING
PRE_TRANSITIONS_PROCESSING = Keywords.PRE_TRANSITIONS_PROCESSING
