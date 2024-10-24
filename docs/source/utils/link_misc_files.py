from pathlib import Path
from typing import Iterable


def create_file_link(source: Path, destination: Path):
    """
    Create a symlink between two files.

    :param source: Path to source file.
    :param destination: Path to link file.
    """
    destination.unlink(missing_ok=True)
    destination.parent.mkdir(exist_ok=True, parents=True)
    destination.symlink_to(source.resolve(), False)


def link_misc_files(files: Iterable[str], configs: dict = None):
    """
    Create links inside the `docs/source/_misc` directory.

    :param files: An iterable of files to link.
    :param configs: Dict with the project root directory in it and other
    parameters of setup() function.
    """
    for file_name in files:
        file = Path(file_name)
        create_file_link(configs["root_dir"] / file, configs["root_dir"] / "docs" / "source" / "_misc" / file.name)
