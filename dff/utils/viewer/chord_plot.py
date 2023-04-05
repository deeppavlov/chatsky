import networkx as nx
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import random

from .utils import get_spaced_colors, normalize_color
from .preprocessing import get_adjacency_dataframe

PI = np.pi


def moduloAB(x, a, b):
    if a >= b:
        raise ValueError("Incorrect inverval ends")
    y = (x - a) % (b - a)
    return y + b if y < 0 else y + a


def test_2PI(x):
    return 0 <= x < 2 * PI


def get_ideogram_ends(ideogram_len, gap):
    ideo_ends = []
    left = 0
    for k in range(len(ideogram_len)):
        right = left + ideogram_len[k]
        ideo_ends.append([left, right])
        left = right + gap
    return ideo_ends


def make_ideogram_arc(R, phi, a=50):
    """
    R is the circle radius
    Phi is a list of the ends angle coordinates of an arc
    a is a parameter that controls the number of points to be evaluated
    """
    if not test_2PI(phi[0]) or not test_2PI(phi[1]):
        phi = [moduloAB(t, 0, 2 * PI) for t in phi]
    length = (phi[1] - phi[0]) % 2 * PI
    nr = 5 if length <= PI / 4 else int(a * length / PI)
    if phi[0] < phi[1]:
        nr = 100

        theta = np.linspace(phi[0], phi[1], nr)
    else:
        phi = [moduloAB(t, -PI, PI) for t in phi]
        # nr = 100
        theta = np.linspace(phi[0], phi[1], nr)
    return R * np.exp(1j * theta)


def map_data(data_matrix, row_value, ideogram_length):
    n = data_matrix.shape[0]  # square, so same as 1
    mapped = np.zeros([n, n])
    for j in range(n):
        mapped[:, j] = ideogram_length * data_matrix[:, j] / row_value
    return mapped


def make_ribbon_ends(mapped_data, ideo_ends, idx_sort):
    n = mapped_data.shape[0]
    ribbon_boundary = np.zeros((n, n + 1))
    for k in range(n):
        start = ideo_ends[k][0]
        ribbon_boundary[k][0] = start
        for j in range(1, n + 1):
            J = idx_sort[k][j - 1]
            ribbon_boundary[k][j] = start + mapped_data[k][J]
            start = ribbon_boundary[k][j]
    return [[(ribbon_boundary[k][j], ribbon_boundary[k][j + 1]) for j in range(n)] for k in range(n)]


def control_pts(angle, radius):
    if len(angle) != 3:
        raise ValueError("Angle must have len = 3")
    b_cplx = np.array([np.exp(1j * angle[k]) for k in range(3)])
    b_cplx[1] = radius * b_cplx[1]
    return list(zip(b_cplx.real, b_cplx.imag))


def ctrl_rib_chords(left, right, radius):
    if len(left) != 2 or len(right) != 2:
        raise ValueError("The arc ends must be elements in a list of len 2")
    return [control_pts([left[j], (left[j] + right[j]) / 2, right[j]], radius) for j in range(2)]


def make_q_bezier(b):
    if len(b) != 3:
        raise ValueError("Control polygon must have 3 points")
    A, B, C = b
    return (
        "M "
        + str(A[0])
        + ","
        + str(A[1])
        + " "
        + "Q "
        + str(B[0])
        + ", "
        + str(B[1])
        + " "
        + str(C[0])
        + ", "
        + str(C[1])
    )


def make_ribbon_arc(theta0, theta1):
    if test_2PI(theta0) and test_2PI(theta1):
        if theta0 < theta1:
            theta0 = moduloAB(theta0, -PI, PI)
            theta1 = moduloAB(theta1, -PI, PI)
            if theta0 * theta1 > 0:
                raise ValueError("Incorrect angle coordinates for ribbon")
        nr = int(40 * (theta0 - theta1) / PI)
        if nr <= 2:
            nr = 3
        theta = np.linspace(theta0, theta1, nr)
        pts = np.exp(1j * theta)
        string_arc = ""
        for k in range(len(theta)):
            string_arc += "L " + str(pts.real[k]) + ", " + str(pts.imag[k]) + " "
        return string_arc
    else:
        raise ValueError("The angle coords for arc ribbon must be [0, 2*PI]")


def make_layout(title):
    xaxis = dict(
        showline=False, automargin=False, zeroline=False, showgrid=False, showticklabels=False, title=dict(standoff=0)
    )
    yaxis = {**xaxis, "scaleanchor": "x"}
    return dict(
        title=title,
        xaxis=xaxis,
        yaxis=yaxis,
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        hovermode="closest",
        shapes=[],
    )


def make_ideo_shape(path, line_color, fill_color):
    return dict(
        line=go.layout.shape.Line(color=line_color, width=0.45),
        path=path,
        type="path",
        fillcolor=fill_color,
        layer="below",
    )


def make_ribbon(left, right, line_color, fill_color, radius=0.2):
    poligon = ctrl_rib_chords(left, right, radius)
    b, c = poligon
    return dict(
        line=go.layout.shape.Line(color=line_color, width=0.5),
        path=make_q_bezier(b)
        + make_ribbon_arc(right[0], right[1])
        + make_q_bezier(c[::-1])
        + make_ribbon_arc(left[1], left[0]),
        type="path",
        fillcolor=fill_color,
        layer="below",
    )


def make_self_rel(line, line_color, fill_color, radius):
    b = control_pts([line[0], (line[0] + line[1]) / 2, line[1]], radius)
    return dict(
        line=dict(color=line_color, width=0.5),
        path=make_q_bezier(b) + make_ribbon_arc(line[1], line[0]),
        type="path",
        fillcolor=fill_color,
        layer="below",
    )


def invPerm(perm):
    inv = [0] * len(perm)
    for i, s in enumerate(perm):
        inv[s] = i
    return inv


def make_filled_chord(adjacency_df: pd.DataFrame, width: int = 800, height: int = 800):  # ,labels):
    labels = list(adjacency_df.columns)
    adjacency_df = adjacency_df.T
    matrix = adjacency_df.to_numpy()
    n = adjacency_df.shape[0]
    row_sum = [np.sum(matrix[k, :]) or 1 for k in range(n)]
    gap = 2 * PI * 10e-8

    ideogram_length = 2 * PI * np.asarray(row_sum) / sum(row_sum) - gap * np.ones(n)
    flow_labels = list(set([i.split(", ")[1] for i in labels]))
    flow_col_dict = {flow: x for flow, x in zip(flow_labels, get_spaced_colors(len(flow_labels)))}
    flow_colors = [normalize_color(flow_col_dict[i.split(", ")[1]], level="flow") for i in labels]
    ideo_colors = [normalize_color(flow_col_dict[i.split(", ")[1]], level="node") for i in labels]
    mapped_data = map_data(matrix, row_sum, ideogram_length)
    idx_sort = np.argsort(mapped_data, axis=1)
    ideo_ends = get_ideogram_ends(ideogram_length, gap)
    ribbon_ends = make_ribbon_ends(mapped_data, ideo_ends, idx_sort)
    ribbon_color = [n * [ideo_colors[k]] for k in range(n)]
    layout = make_layout(" ")
    ribbon_info = []
    radii_sribb = [0.2] * n
    for k in range(n):
        sigma = idx_sort[k]
        sigma_inv = invPerm(sigma)
        for j in range(k, n):
            if adjacency_df.iloc[k, j] == 0 and adjacency_df.iloc[j, k] == 0:
                continue
            eta = idx_sort[j]
            eta_inv = invPerm(eta)
            left = ribbon_ends[k][sigma_inv[j]]
            if j == k:
                layout["shapes"].append(make_self_rel(left, "rgb(175,175,175)", ideo_colors[k], radius=radii_sribb[k]))
                z = 0.9 * np.exp(1j * (left[0] + left[1]) / 2)
                text = labels[k] + " {0} transitions to ".format(adjacency_df.iloc[k, k])
                ribbon_info.append(
                    go.Scatter(
                        x=[z.real],
                        y=[z.imag],
                        mode="markers",
                        text=text,
                        hoverinfo="text",
                        marker=dict(size=0.5, color=ideo_colors[k]),
                    )
                )
            else:
                right = ribbon_ends[j][eta_inv[k]]
                zi = 0.9 * np.exp(1j * (left[0] + left[1]) / 2)
                zf = 0.9 * np.exp(1j * (right[0] + right[1]) / 2)

                texti = labels[k] + " {0} transitions to ".format(matrix[k][j]) + labels[j]
                textf = labels[j] + " {0} transitions to ".format(matrix[j][k]) + labels[k]

                ribbon_info.append(
                    go.Scatter(
                        x=[zi.real],
                        y=[zi.imag],
                        mode="markers",
                        text=texti,
                        hoverinfo="text",
                        marker=dict(size=0.5, color=ribbon_color[k][j]),
                    )
                )
                ribbon_info.append(
                    go.Scatter(
                        x=[zf.real],
                        y=[zf.imag],
                        mode="markers",
                        text=textf,
                        hoverinfo="text",
                        marker=dict(size=0.5, color=ribbon_color[j][k]),
                    )
                )
                right = (right[1], right[0])
                if matrix[k][j] > matrix[j][k]:
                    color_of_highest = ribbon_color[k][j]
                else:
                    color_of_highest = ribbon_color[j][k]
                layout["shapes"].append(make_ribbon(left, right, "rgb(175, 175, 175)", color_of_highest))
    ideograms = []

    for k in range(len(ideo_ends)):
        node_z = make_ideogram_arc(1.1, ideo_ends[k])
        node_zi = make_ideogram_arc(1.0, ideo_ends[k])
        flow_z = make_ideogram_arc(1.1 + 0.2, ideo_ends[k])
        flow_zi = make_ideogram_arc(1.1, ideo_ends[k])
        for z, zi, label, meta, color in [
            (node_z, node_zi, labels[k], "node", ideo_colors[k]),
            (flow_z, flow_zi, labels[k].split(", ")[1], "flow", flow_colors[k]),
        ]:
            m = len(z)
            n = len(zi)
            ideograms.append(
                go.Scatter(
                    x=z.real,
                    y=z.imag,
                    mode="lines",
                    name=label,
                    line=dict(color=color, shape="spline", width=0.25),
                    text=label,
                    hoverinfo="text",
                    meta=[meta],
                )
            )
            path = "M "
            for s in range(m):
                path += str(z.real[s]) + ", " + str(z.imag[s]) + " L "
            Zi = np.array(zi.tolist()[::-1])
            for s in range(m):
                path += str(Zi.real[s]) + ", " + str(Zi.imag[s]) + " L "
            path += str(z.real[0]) + " ," + str(z.imag[0])
            layout["shapes"].append(make_ideo_shape(path, "rgb(150,150,150)", color))

    layout["width"] = width
    layout["height"] = height
    data = ideograms + ribbon_info
    fig = {"data": data, "layout": layout}
    return fig


def add_annotations(figure: go.Figure):
    def add_annotations_inner(trace):
        if not trace.meta or "node" not in trace.meta:
            return ()
        rand = 1.6
        anno = figure.add_annotation(
            x=trace.x[len(trace.x) // 2] * rand,
            y=trace.y[len(trace.y) // 2] * rand,
            text=trace.name.replace(", ", "<br>"),
            showarrow=False,
            align="right",
            font_size=8,
        )
        return anno

    return add_annotations_inner


def get_plot(
    nx_graph: nx.Graph,
    random_seed: int = 1,
    **kwargs,  # for cli integration
) -> go.Figure:
    random.seed(random_seed)
    adj_df = get_adjacency_dataframe(nx_graph)
    figure_data = make_filled_chord(adjacency_df=adj_df)
    figure = go.Figure(figure_data)
    figure.for_each_trace(add_annotations(figure))
    return figure
