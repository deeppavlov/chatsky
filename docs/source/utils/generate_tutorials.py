from pathlib import Path
from shutil import copy
from typing import List, Optional, Set, Union, Tuple


def create_notebook_link(source: Path, destination: Path):
    """
    Create a symlink between two files.
    Used to create links to tutorials under docs/source/tutorials/ root.

    :param source: Path to source file (in tutorials/ dir).
    :param destination: Path to link file (in docs/source/tutorials/ dir).
    """
    destination.unlink(missing_ok=True)
    destination.parent.mkdir(exist_ok=True, parents=True)
    destination.symlink_to(source.resolve(), False)


def generate_nb_gallery(package: str, files: List[Path]) -> str:
    """
    Generate a gallery of tutorials.

    :param package: Package to join into a gallery (effectively a common tutorial link prefix).
    :param files: List of all tutorial links.
    """
    included = "\n   ".join(file.name for file in files if file.name.startswith(package))
    return f"""
.. nbgallery::
   {included}
"""


def create_index_file(
    included: Union[Tuple[str, str], Tuple[str, str, List[Tuple[str, str]]]],
    files: List[Path],
    destination: Path,
):
    """
    Create a package index file.
    Contains nbgalleries of files inside the package (and subpackages).

    :param included: A pair of package path and alias with or without list of subpackages.
    :param files: List of all tutorial links.
    :param destination: Path to the index file.
    """
    title = included[1]
    contents = f""":orphan:

.. This is an auto-generated RST index file representing tutorials directory structure

{title}
{"=" * len(title)}
"""
    if len(included) == 2:
        contents += generate_nb_gallery(included[0], files)
    else:
        for subpackage in included[2]:
            contents += f"\n{subpackage[1]}\n{'-' * len(subpackage[1])}\n"
            contents += generate_nb_gallery(f"{included[0]}.{subpackage[0]}", files)

    destination.parent.mkdir(exist_ok=True, parents=True)
    destination.write_text(contents)


def sort_tutorial_file_tree(files: Set[Path]) -> List[Path]:
    """
    Sort files alphabetically; for the tutorial files (whose names start with number) numerical sort is applied.

    :param files: Files list to sort.
    """
    tutorials = {file for file in files if file.stem.split("_")[0].isdigit()}

    def sort_key(tutorial_file_name: Path) -> float:
        tutorial_number = float(tutorial_file_name.stem.split("_")[0])

        # full tutorials should go after tutorials with the same number
        if tutorial_file_name.stem.endswith("_full"):
            return tutorial_number + 0.5
        return tutorial_number

    return sorted(tutorials, key=sort_key) + sorted(files - tutorials)


def iterate_tutorials_dir_generating_links(source: Path, dest: Path, base: str) -> List[Path]:
    """
    Recursively travel through tutorials directory, creating copies for all files under /tmp_dir/docs/source/tutorials/ root.
    Created copied files have absolute path name matching source file tree structure.

    :param source: Tutorials root (usually tutorials/).
    :param dest: Tutorials destination (usually docs/source/tutorials/).
    :param base: Absolute path to current dir (will be used for link file naming).
    """
    if not source.is_dir():
        raise Exception(f"Entity {source} appeared to be a file during processing!")
    links = list()
    for entity in [obj for obj in sort_tutorial_file_tree(set(source.glob("./*"))) if not obj.name.startswith("__")]:
        base_name = f"{base}.{entity.name}"
        if entity.is_file() and entity.suffix in (".py", ".ipynb"):
            base_path = Path(base_name)
            create_notebook_link(entity, Path(base_name))
            links += [base_path]
        elif entity.is_dir() and not entity.name.startswith("_"):
            links += iterate_tutorials_dir_generating_links(entity, dest, base_name)
    return links


def generate_tutorial_links_for_notebook_creation(
    include: Optional[List[Union[Tuple[str, str], Tuple[str, str, List[Tuple[str, str]]]]]] = None,
    exclude: Optional[List[str]] = None,
    source: str = "tutorials",
    destination: str = "docs/source/tutorials",
):
    """
    Generate symbolic links to tutorials files (tutorials/) in docs directory (docs/source/tutorials/).
    That is required because Sphinx doesn't allow to include files from parent directories into documentation.
    Also, this function creates index files inside each generated folder.
    That index includes each folder contents, so any folder can be imported with 'folder/index'.

    :param include: Files to copy (supports file templates, like *).
    :param exclude: Files to skip (supports file templates, like *).
    :param source: Tutorials root, default: 'tutorials/'.
    :param destination: Destination root, default: 'docs/source/tutorials/'.
    """
    include = [("tutorials", "Tutorials")] if include is None else include
    exclude = list() if exclude is None else exclude
    dest = Path(destination)

    flattened = list()
    for package in include:
        if len(package) == 2:
            flattened += [package[0]]
        else:
            flattened += [f"{package[0]}.{subpackage[0]}" for subpackage in package[2]]

    links = iterate_tutorials_dir_generating_links(Path(source), dest, f"{source}/tutorials")
    filtered_links = list()
    for link in links:
        link_included = len(list(flat for flat in flattened if link.name.startswith(flat))) > 0
        link_excluded = len(list(pack for pack in exclude if link.name.startswith(pack))) > 0
        if link_included and not link_excluded:
            filtered_links += [link]

    for included in include:
        create_index_file(
            included, filtered_links, dest / Path(f"index_{included[1].replace(' ', '_').lower()}.rst"), dest
        )
