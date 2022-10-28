from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional


def create_nblink(file: Path, notebook_path: Path):
    file.parent.mkdir(exist_ok=True, parents=True)
    file.symlink_to(notebook_path.resolve(), False)


def create_index(file: Path, index: List[Path]):
    title = " ".join(word.capitalize() for word in file.parent.stem.split("_"))
    directories = "\n   ".join(directory.stem for directory in index)
    contents = f"""
.. This is an auto-generated RST index file representing examples directory structure

{title}
{"=" * len(title)}

.. toctree::
   :glob:
   :caption: {title}

   {directories}
"""
    file.parent.mkdir(exist_ok=True, parents=True)
    file.write_text(contents)


def process_dir(path: Path, exclude: List[str]):
    if not path.is_dir():
        raise Exception(f"Entity {path} appeared to be a file during processing!")
    includes = list()
    for entity in path.glob("*"):
        doc_path = Path(f"docs/source/examples") / entity.relative_to("examples/")
        if not entity.name.startswith("__"):
            if entity.is_file() and entity.suffix in (".py", ".ipynb") and any(fnmatch(str(entity.relative_to(".")), ex) for ex in exclude):
                includes.append(doc_path)
                create_nblink(doc_path, entity)
            elif entity.is_dir():
                includes.append(doc_path)
                process_dir(entity, exclude)
    create_index(Path(f"docs/source/examples") / path.relative_to("examples/") / Path("index.rst"), includes)


def generate_links(include: Optional[List[str]] = None):
    process_dir(Path("examples/"), ["*"] if include is None else include)
