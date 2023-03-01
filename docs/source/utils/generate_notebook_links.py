from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional, Set


def create_notebook_link(file: Path, notebook_path: Path):
    """
    Create a symlink between two files.
    Used to create links to examples under docs/source/examples/ root.

    :param file: File to create link from (a code example).
    :param notebook_path: Path to create the link.
    """
    file.parent.mkdir(exist_ok=True, parents=True)
    file.symlink_to(notebook_path.resolve(), False)


def create_directory_index_file(file: Path, index: List[str]):
    """
    Create a directory index file.
    Contains a nbgallery of files inside the directory.

    :param file: Path to directory index file (file name is usually 'index.rst').
    :param index: List of the files to include into the directory, should be sorted previously.
    """
    title = " ".join(word.capitalize() for word in file.parent.stem.split("_"))
    directories = "\n   ".join(directory for directory in index)
    contents = f""":orphan:

.. This is an auto-generated RST index file representing examples directory structure

{title}
{"=" * len(title)}

.. nbgallery::
   :glob:

   {directories}
"""
    file.parent.mkdir(exist_ok=True, parents=True)
    file.write_text(contents)


def sort_example_file_tree(files: Set[Path]) -> List[Path]:
    """
    Sort files alphabetically; for the example files (whose names start with number) numerical sort is applied.

    :param files: Files list to sort.
    """
    examples = {file for file in files if file.stem.split("_")[0].isdigit()}
    return sorted(examples, key=lambda file: int(file.stem.split("_")[0])) + sorted(files - examples)


def iterate_dir_generating_notebook_links(
    current: Path, source: str, dest: str, include: List[str], exclude: List[str]
) -> List[str]:
    """
    Recursively travel through examples directory, creating links for all files under docs/source/examples/ root.
    Also creates indexes for all created links for them to be easily included into RST documentation.

    :param current: Path being searched currently.
    :param source: Examples root (usually examples/).
    :param dest: Examples destination (usually docs/source/examples/).
    :param include: List of files to include to search (is applied before exclude list).
    :param exclude: List of files to exclude from search (is applied after include list).
    """
    dest_path = Path(dest)
    if not current.is_dir():
        raise Exception(f"Entity {current} appeared to be a file during processing!")
    includes = list()
    for entity in sort_example_file_tree(set(current.glob("./*"))):
        doc_path = dest_path / entity.relative_to(source)
        if not entity.name.startswith("__"):
            if (
                entity.is_file()
                and entity.suffix in (".py", ".ipynb")
                and any(fnmatch(str(entity.relative_to(".")), inc) for inc in include)
                and not any(fnmatch(str(entity.relative_to(".")), exc) for exc in exclude)
            ):
                if not entity.name.startswith("_"):
                    includes.append(doc_path.name)
                create_notebook_link(doc_path, entity)
            elif entity.is_dir() and not entity.name.startswith("_"):
                if len(iterate_dir_generating_notebook_links(entity, source, dest, include, exclude)) > 0:
                    includes.append(f"{doc_path.name}/index")
    if len(includes) > 0:
        create_directory_index_file(dest_path / current.relative_to(source) / Path("index.rst"), includes)
    return includes


def generate_example_links_for_notebook_creation(
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    source: str = "examples/",
    destination: str = "docs/source/examples/",
):
    """
    Generate symbolic links to examples files (examples/) in docs directory (docs/source/examples/).
    That is required because Sphinx doesn't allow to include files from parent directories into documentation.
    Also, this function creates index files inside each generated folder.
    That index includes each folder contents, so any folder can be imported with 'folder/index'.

    :param include: Files to copy (supports file templates, like *).
    :param exclude: Files to skip (supports file templates, like *).
    :param source: Examples root, default: 'examples/'.
    :param destination: Destination root, default: 'docs/source/examples/'.
    """
    iterate_dir_generating_notebook_links(
        Path(source),
        source,
        destination,
        ["**"] if include is None else include,
        [] if exclude is None else exclude,
    )
