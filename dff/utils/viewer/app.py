import plotly.graph_objects as go

import dash
from dash import dcc
from dash import html


def create_app(fig: go.Figure):
    fig.update_layout(title="Script Graph View")
    fig.update_xaxes(showticklabels=False).update_yaxes(showticklabels=False)
    app = dash.Dash()
    app.layout = html.Div(
        [dcc.Graph(id="script", figure=fig, style={"width": "160vh", "height": "120vh", "margin": "auto"})]
    )
    return app
