from enum import Enum


class State(str):
    def __new__(cls, other):
        if isinstance(other, tuple):
            return tuple(super(State, cls).__new__(cls, x) for x in other)
        else:
            return super(State, cls).__new__(cls, other)

    def __eq__(self, other):
        if isinstance(other, Enum):
            return str.__eq__(self, str(other))
        else:
            return str.__eq__(self, other)

    def __hash__(self):
        return str.__hash__(self)
