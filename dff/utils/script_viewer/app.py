from base64 import b64encode
from io import BytesIO

import plotly.graph_objects as go
from graphviz import Digraph

import dash
from dash import dcc
from dash import html


def create_app(plot: Digraph):
    _bytes = plot.pipe(format="png")
    prefix = "data:image/png;base64,"
    with BytesIO(_bytes) as stream:
        base64 = prefix + b64encode(stream.getvalue()).decode("utf-8")
    fig = go.Figure(go.Image(source=base64))
    fig.update_layout(title="Script Graph View")
    fig.update_xaxes(showticklabels=False).update_yaxes(showticklabels=False)
    app = dash.Dash()
    app.layout = html.Div(
        [dcc.Graph(id="script", figure=fig, style={"width": "120vh", "height": "120vh", "margin": "auto"})]
    )
    return app
