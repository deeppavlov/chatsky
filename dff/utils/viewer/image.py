from graphviz import Digraph
import plotly.graph_objects as go
from plotly.io import write_image


def graphviz_image(plot: Digraph, output_file: str, format: str = "png") -> None:
    if format == "dot":
        plot.render(filename=output_file)
        return

    _bytes = plot.pipe(format=format)
    with open(output_file, "wb+") as file:
        file.write(_bytes)


def plotly_image(plot: go.Figure, output_file: str, format: str = "png") -> None:
    write_image(plot, output_file, format=format)
