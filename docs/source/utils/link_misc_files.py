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


def link_misc_files(files: Iterable[str], root_dir: Path):
    """
    Create links inside the `docs/source/_misc` directory.

    :param files: An iterable of files to link.
    """
    for file_name in files:
        file = Path(file_name)
        create_file_link(root_dir / file, root_dir / Path("docs/source/_misc") / file.name)
