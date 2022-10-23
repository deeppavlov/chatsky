from graphviz import Digraph


def create_image(plot: Digraph, output_file: str, format: str = "png") -> None:
    _bytes = plot.pipe(format=format)
    with open(output_file, "wb") as file:
        file.write(_bytes)
