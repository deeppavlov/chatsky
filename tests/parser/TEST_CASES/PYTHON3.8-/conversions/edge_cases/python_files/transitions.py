from .variables import number, label, condition


transitions = {
    1: "cnd",
    "two": "label",
    number: {
        label: condition,
    },
    "set": {
        1,
        2,
    }
}
