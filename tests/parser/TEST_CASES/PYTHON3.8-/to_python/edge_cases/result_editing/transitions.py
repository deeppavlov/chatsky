from .variables import number
from .variables import label
from .variables import condition

transitions = {
    1: 'cnd',
    'two': 'label',
    number: {
        label: condition,
    },
    'set': {1, 2},
}
