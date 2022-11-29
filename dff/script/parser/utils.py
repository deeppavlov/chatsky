from typing import Union, Iterable
from collections.abc import Iterable as abc_Iterable

# todo: remove this when python3.8 support is dropped
def remove_prefix(self: str, prefix: str) -> str:
    if self.startswith(prefix):
        return self[len(prefix):]
    else:
        return self[:]


# todo: remove this when python3.8 support is dropped
def remove_suffix(self: str, suffix: str) -> str:
    # suffix='' should not call self[:-0].
    if suffix and self.endswith(suffix):
        return self[:-len(suffix)]
    else:
        return self[:]


def is_instance(obj: object, cls: Union[str, type, Iterable[Union[str, type]]]):
    def _is_instance(_cls: Union[str, type]):
        if isinstance(_cls, str):
            return obj.__class__.__module__ + "." + obj.__class__.__name__ == _cls
        return isinstance(obj, _cls)

    if isinstance(cls, (str, type)):
        return _is_instance(cls)
    if isinstance(cls, abc_Iterable):
        return any(map(_is_instance, cls))
    else:
        raise TypeError(f"{type(cls)}")
