from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional


def create_notebook_link(file: Path, notebook_path: Path):
    file.parent.mkdir(exist_ok=True, parents=True)
    file.symlink_to(notebook_path.resolve(), False)


def create_directory_index_file(file: Path, index: List[str]):
    title = " ".join(word.capitalize() for word in file.parent.stem.split("_"))
    directories = "\n   ".join(directory for directory in index)
    contents = f"""
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


def iterate_dir_generating_notebook_links(path: Path, dest: str, include: List[str], exclude: List[str]) -> List[str]:
    if not path.is_dir():
        raise Exception(f"Entity {path} appeared to be a file during processing!")
    includes = list()
    for entity in path.glob("./*"):
        doc_path = Path(dest) / entity.relative_to("examples/")
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
                if len(iterate_dir_generating_notebook_links(entity, dest, include, exclude)) > 0:
                    includes.append(f"{doc_path.name}/index")
    if len(includes) > 0:
        create_directory_index_file(Path(dest) / path.relative_to("examples/") / Path("index.rst"), includes)
    return includes


def generate_example_links_for_notebook_creation(
    include: Optional[List[str]] = None,
    destination: str = "examples",
    exclude: Optional[List[str]] = None,
):
    iterate_dir_generating_notebook_links(
        Path("examples/"),
        f"docs/source/{destination}",
        ["**"] if include is None else include,
        [] if exclude is None else exclude,
    )
