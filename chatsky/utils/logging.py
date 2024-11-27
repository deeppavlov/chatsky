from typing import Union


def collapse_num_list(num_list: Union[list[int], list[float]]) -> str:
    """
    Produce representation for a list of numbers while collapsing large lists.

    For lists with 10 or fewer items return the representation of the list.
    Otherwise, return a string with the minimum and maximum items as well as the number of items.
    """
    if len(num_list) > 10:
        return f"{min(num_list)} .. {max(num_list)} ({len(num_list)} items)"
    else:
        return repr(num_list)
