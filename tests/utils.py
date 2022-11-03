import os
import pathlib


def get_path_from_tests_to_current_dir(file: str, separator: str = os.sep) -> str:
    parents = []
    for parent in pathlib.Path(file).parents:
        if "tests" == parent.name:
            break
        parents += [parent.name]

    dot_path_to_addon = separator.join(reversed(parents))
    return dot_path_to_addon
