from graphviz import Digraph


def image(plot: Digraph, output_file: str, format: str = "png") -> None:
    if format == "dot":
        plot.render(filename=output_file)
        return

    _bytes = plot.pipe(format=format)
    with open(output_file, "wb") as file:
        file.write(_bytes)
