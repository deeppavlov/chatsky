import pathlib


def get_dot_path_from_tests_to_current_dir(file):
    parents = []
    for parent in pathlib.Path(file).parents:
        if "tests" == parent.name:
            break
        parents += [parent.name]

    dot_path_to_addon = ".".join(reversed(parents))
    return dot_path_to_addon
