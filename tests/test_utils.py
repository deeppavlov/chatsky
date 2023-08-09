import os
import pathlib


tests_to_skip = {var for var in os.environ["TESTS_TO_SKIP"].split(":") if var.startswith("db_")}


def get_path_from_tests_to_current_dir(file: str, separator: str = os.sep) -> str:
    parents = []
    for parent in pathlib.Path(file).parents:
        if "tests" == parent.name:
            break
        parents += [parent.name]

    dot_path_to_addon = separator.join(reversed(parents))
    return dot_path_to_addon
