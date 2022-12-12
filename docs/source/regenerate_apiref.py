from pathlib import Path
from typing import List, Optional, Tuple, Dict


def generate_doc_container(file: Path, includes: List[Path]):
    title = file.stem
    sources = "\n   ".join(str(include.stem) for include in includes)
    contents = f""":orphan:

.. This is an auto-generated RST file representing documentation source directory structure

{title}
{"=" * len(title)}

.. toctree::
   :caption: {title}

   {sources}
"""
    file.with_name(f"index_{file.name}").write_text(contents)


def regenerate_apiref(paths: Optional[List[Tuple[str, str]]] = None, destination: str = "apiref"):
    paths = list() if paths is None else paths
    source = Path(f"./docs/source/{destination}")
    doc_containers: Dict[str, List[Path]] = dict()

    for doc_file in iter(source.glob("./*.rst")):
        contents = doc_file.read_text()
        if ".. toctree::" in contents:
            doc_file.unlink()
            continue

        container = next((alias for flat, alias in paths if doc_file.name.startswith(flat)), None)
        if container is None:
            doc_file.unlink()
        else:
            doc_containers[container] = doc_containers.get(container, list()) + [doc_file]

    for name, files in doc_containers.items():
        generate_doc_container(source / Path(f"{name}.rst"), files)
