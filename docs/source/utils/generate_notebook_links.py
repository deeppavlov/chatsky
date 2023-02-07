from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional, Set


def create_notebook_link(file: Path, notebook_path: Path):
    file.parent.mkdir(exist_ok=True, parents=True)
    file.symlink_to(notebook_path.resolve(), False)


def create_directory_index_file(file: Path, index: List[str]):
    title = " ".join(word.capitalize() for word in file.parent.stem.split("_"))
    directories = "\n   ".join(directory for directory in index)
    contents = f""":orphan:

.. This is an auto-generated RST index file representing examples directory structure

{title}
{"=" * len(title)}

.. nbgallery::
   :glob:
   :caption: {title}

   {directories}
"""
    file.parent.mkdir(exist_ok=True, parents=True)
    file.write_text(contents)


def sort_example_file_tree(files: Set[Path]) -> List[Path]:
    examples = {file for file in files if file.stem.split("_")[0].isdigit()}
    return sorted(examples, key=lambda file: int(file.stem.split("_")[0])) + sorted(files - examples)


def iterate_dir_generating_notebook_links(
    current: Path, source: str, dest: str, include: List[str], exclude: List[str]
) -> List[str]:
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
    iterate_dir_generating_notebook_links(
        Path(source),
        source,
        destination,
        ["**"] if include is None else include,
        [] if exclude is None else exclude,
    )
