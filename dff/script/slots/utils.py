from typing import Callable, TypeVar, Union

import wrapt


T = TypeVar("T")


def singleton(result: Union[T, None] = None) -> Callable[..., T]:
    @wrapt.decorator
    def singleton_decorator(cls: Callable[..., T], _, args, kwargs) -> T:
        nonlocal result
        if result is None:
            result = cls(*args, **kwargs)
        return result

    return singleton_decorator
