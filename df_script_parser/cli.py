import libcst as cst
import logging
from pathlib import Path
import typing as tp
from .parse import Parser
from .processors import NodeProcessor, Disambiguator
import argparse
from .dumpers_loaders import ryaml, pp
from black import format_file_in_place, FileMode, WriteBack


def is_dir(path: str) -> Path:
    path = Path(path)
    if path.is_dir():
        return path
    raise argparse.ArgumentTypeError(f"Not a dir: {path}")


def is_file(path: str) -> Path:
    path = Path(path)
    if path.is_file():
        return path
    raise argparse.ArgumentTypeError(f"Not a file: {path}")


def py2yaml(
    input_file: tp.Union[str, Path],
    output_dir: tp.Union[str, Path],
    safe_mode: bool = True,
) -> None:
    """Parse python script INPUT_FILE into import.yaml containing information about imports used in the script,
    script.yaml containing a dictionary found inside the file.
    If the file contains an instance of df_engine.Actor class its arguments will be parsed and special labels
    will be placed in script.yaml.

    All the files are stored in OUTPUT_DIR."""
    input_file = Path(input_file)
    output_dir = Path(output_dir)

    with open(input_file, "r") as f:
        parsed_file = cst.parse_module(f.read())

    logging.info(f"File {input_file} parsed")

    transformer = Parser(input_file.parent, safe_mode=safe_mode)

    parsed_file.visit(transformer)

    script = NodeProcessor(
        transformer.dict_node,
        list(transformer.imports),
        start_label=transformer.args.get("start_label"),
        fallback_label=transformer.args.get("fallback_label"),
        safe_mode=safe_mode,
    ).result

    transformer.imports.dump(output_dir)
    logging.info("Imports dumped")
    with open(output_dir / "script.yaml", "w") as f:
        ryaml.dump(script, f)
        logging.info("Script dumped")


def py2yaml_cli():
    parser = argparse.ArgumentParser(description=py2yaml.__doc__)
    parser.add_argument(
        "input_file",
        metavar="INPUT_FILE",
        help="Python script to parse.",
        type=is_file,
    )
    parser.add_argument(
        "output_dir",
        metavar="OUTPUT_DIR",
        help="Directory to store parser output in.",
        type=is_dir,
    )
    args = parser.parse_args()
    py2yaml(**vars(args))


def yaml2py(
    input_dir: tp.Union[str, Path],
    output_file: tp.Union[str, Path],
) -> None:
    """Generate a python script OUTPUT_FILE from import.yaml and script.yaml inside the INPUT_DIR.

    Generation rules:

    * If a string inside the script.yaml is a correct python code within the context of imports it will be displayed in the OUTPUT_FILE without quotations. If you want to specify how the string should be displayed use !str tag for strings and !py tag for lines of code.
    * If a {dictionary {key / value} / list value} has a !start or !start:str or !start:py tag the path to that element will be stored in a start_label variable.
    * If a {dictionary {key / value} / list value} has a tag !fallback or !fallback:str or !fallback:py tag the path to that key will be stored in a fallback_label variable.
    """
    input_dir = Path(input_dir)
    output_file = Path(output_file)
    with open(output_file, "w") as output:
        # write imports
        with open(input_dir / "import.yaml", "r") as f:
            loaded_imports = ryaml.load(f)
        imports = []
        for key in loaded_imports.keys():
            for module in loaded_imports[key].keys():
                for code in loaded_imports[key][module]:
                    imports.append(code)
        output.write("\n".join(imports) + "\n\n")

        with open(input_dir / "script.yaml", "r") as f:
            script = ryaml.load(f)
            logging.debug(script)
        disambiguation = Disambiguator(script, imports)
        output.write("\nscript = ")
        pp(disambiguation.result, output)
        output.write("\nstart_label = ")
        pp(
            tuple(disambiguation.start_label) if disambiguation.start_label else None,
            output,
        )
        output.write("\nfallback_label = ")
        pp(
            tuple(disambiguation.fallback_label) if disambiguation.fallback_label else None,
            output,
        )
        output.write("\n")
        output.write("from df_engine.core import Actor\n" "\nactor = Actor(script, start_label, fallback_label)\n")
    format_file_in_place(output_file, fast=False, mode=FileMode(), write_back=WriteBack.YES)


def yaml2py_cli():
    parser = argparse.ArgumentParser(description=yaml2py.__doc__)
    parser.add_argument(
        "input_dir",
        metavar="INPUT_DIR",
        help="Directory with yaml files.",
        type=is_dir,
    )
    parser.add_argument(
        "output_file",
        metavar="OUTPUT_FILE",
        help="Python file, output.",
        type=is_file,
    )
    args = parser.parse_args()
    yaml2py(**vars(args))
