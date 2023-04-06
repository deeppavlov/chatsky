import random
from base64 import b64encode
from io import BytesIO

from graphviz import Digraph
import plotly.graph_objects as go


def graphviz_to_plotly(plot: Digraph) -> go.Figure:
    _bytes = plot.pipe(format="png")
    prefix = "data:image/png;base64,"
    with BytesIO(_bytes) as stream:
        base64 = prefix + b64encode(stream.getvalue()).decode("utf-8")
    fig = go.Figure(go.Image(source=base64))
    return fig


def get_random_colors():
    target_colors = ["#96B0AF", "#C6AE82", "#F78378", "#FF7B9C", "#D289AB", "#86ACD5", "#86ACD5", "#F8D525", "#F6AE2D"]
    reserve = []
    for element in target_colors:
        yield element
        reserve.append(random.choice(target_colors))
    while reserve:
        yield reserve.pop(0)


def get_spaced_colors(n):
    colors = [
        f"rgb({int(color[1:3], base=16)}, {int(color[3:5], base=16)}, {int(color[5:7], base=16)})"
        for _, color in zip(range(n), get_random_colors())
    ]
    return colors or None


def normalize_color(color: str, level: str = "node"):
    opacity_value = 95
    if level == "node":
        r, g, b = color.strip("rgb()").split(", ")
        r, g, b = (
            (int(r) + random.randint(-25, 25)),
            (int(g) + random.randint(-25, 25)),
            (int(b) + random.randint(-25, 25)),
        )
        r = 0 if r < 0 else 255 if r > 255 else r
        g = 0 if g < 0 else 255 if g > 255 else g
        b = 0 if b < 0 else 255 if b > 255 else b
        color = f"rgb({r}, {g}, {b})"
        opacity_value = 70
    normalized = color[:3] + "a" + color[3:-1] + f",.{opacity_value}" + color[-1]
    return normalized
