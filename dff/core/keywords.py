from enum import Enum, auto


class Keywords(Enum):
    GLOBAL = auto()
    LOCAL = auto()
    TRANSITIONS = auto()
    RESPONSE = auto()
    PROCESSING = auto()
    MISC = auto()


GLOBAL = Keywords.GLOBAL
LOCAL = Keywords.LOCAL
TRANSITIONS = Keywords.TRANSITIONS
RESPONSE = Keywords.RESPONSE
PROCESSING = Keywords.PROCESSING
MISC = Keywords.MISC


# TRANSITIONS = "transitions"
# RESPONSE = "response"
# PROCESSING = "processing"
# MISC = "misc"
