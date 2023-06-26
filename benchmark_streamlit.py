import streamlit as st
import json
from pathlib import Path
import pandas as pd
from pympler import asizeof
from humanize import naturalsize
import altair as alt


st.set_page_config(
    page_title="DB benchmark",
    layout="wide",
    initial_sidebar_state="expanded",
)


benchmark_results_files = Path("benchmark_results_files.json")

if not benchmark_results_files.exists():
    with open(benchmark_results_files, "w", encoding="utf-8") as fd:
        json.dump([], fd)

if "benchmark_files" not in st.session_state:
    with open(benchmark_results_files, "r", encoding="utf-8") as fd:
        st.session_state["benchmark_files"] = json.load(fd)

if "benchmarks" not in st.session_state:
    st.session_state["benchmarks"] = {}

    for file in st.session_state["benchmark_files"]:
        with open(file, "r", encoding="utf-8") as fd:
            st.session_state["benchmarks"][file] = json.load(fd)

if "compare" not in st.session_state:
    st.session_state["compare"] = []


def get_diff(last_metric, first_metric):
    if st.session_state["percent_compare"]:
        return f"{(last_metric / first_metric - 1):.3%}"
    else:
        return f"{last_metric - first_metric:.3}"


def add_metrics(container, value_benchmark, diff_benchmark=None):
    write, read, update, read_update = container.columns(4)
    column_names = ("write", "read", "update", "read+update")

    if not value_benchmark["success"]:
        values = {key: "-" for key in column_names}
        diffs = None
    else:
        values = {
            key: value_benchmark["average_results"][f"pretty_{key}"] for key in column_names
        }

        if diff_benchmark is not None:
            if not diff_benchmark["success"]:
                diffs = {key: "-" for key in column_names}
            else:
                diffs = {
                    key: get_diff(
                        value_benchmark["average_results"][f"pretty_{key}"],
                        diff_benchmark["average_results"][f"pretty_{key}"]
                    ) for key in column_names
                }
        else:
            diffs = None

    columns = {
        "write": write,
        "read": read,
        "update": update,
        "read+update": read_update,
    }

    for column_name, column in columns.items():
        column.metric(
            column_name.title(),
            values[column_name],
            delta=diffs[column_name] if diffs else None,
            delta_color="inverse"
        )


def get_opposite_benchmarks(benchmark_set, benchmark):
    compare_params = (
        ("db_factory", "uri"),
        ("context_num", ),
        ("from_dialog_len", ),
        ("to_dialog_len", ),
        ("step_dialog_len", ),
        ("message_lengths", ),
        ("misc_lengths", ),
    )

    def get_param(bench, param):
        if len(param) == 1:
            return bench.get(param[0])
        else:
            return get_param(bench.get(param[0]), param[1:])

    opposite_benchmarks = [
        opposite_benchmark
        for opposite_benchmark in benchmark_set["benchmarks"].values()
        if opposite_benchmark["uuid"] != benchmark["uuid"] and all(
            get_param(benchmark, param) == get_param(opposite_benchmark, param) for param in compare_params
        )
    ]

    return opposite_benchmarks


st.sidebar.text(f"Benchmarks take {naturalsize(asizeof.asizeof(st.session_state['benchmarks']))} RAM")

st.sidebar.divider()

st.sidebar.checkbox("Compare dev and partial in view tab", value=True, key="partial_compare_checkbox")
st.sidebar.checkbox("Percent comparison", value=True, key="percent_compare")

add_tab, view_tab, compare_tab, mass_compare_tab = st.tabs(["Benchmark sets", "View", "Compare", "Mass compare"])


###############################################################################
# Benchmark file manipulation tab
# Allows adding and deleting benchmark files
###############################################################################

with add_tab:
    benchmark_list = []

    for file, benchmark_set in st.session_state["benchmarks"].items():
        benchmark_list.append(
            {
                "file": file,
                "name": benchmark_set["name"],
                "description": benchmark_set["description"],
                "uuid": benchmark_set["uuid"],
                "delete": False,
            }
        )

    df = pd.DataFrame(data=benchmark_list)
    edited_df = st.data_editor(df, disabled=("file", "name", "description", "uuid"))

    delist_container = st.container()
    delist_container.divider()

    def delist_benchmarks():
        delisted_sets = [f"{name} ({uuid})"
                         for name, uuid in edited_df.loc[edited_df["delete"]][["name", "uuid"]].values
                         ]

        st.session_state["compare"] = [
            item for item in st.session_state["compare"] if item["benchmark_set"] not in delisted_sets
        ]

        files_to_delist = edited_df.loc[edited_df["delete"]]["file"]
        st.session_state["benchmark_files"] = list(set(st.session_state["benchmark_files"]) - set(files_to_delist))
        for file in files_to_delist:
            del st.session_state["benchmarks"][file]
            delist_container.text(f"Delisted {file}")


    delist_container.button(label="Delist selected benchmark sets", on_click=delist_benchmarks)

    add_container = st.container()
    add_container.divider()

    add_container.text_input(label="Benchmark set file", key="add_benchmark_file")

    def add_benchmark():
        benchmark_file = st.session_state["add_benchmark_file"]
        if benchmark_file == "":
            return

        if benchmark_file in st.session_state["benchmark_files"]:
            add_container.warning("Benchmark file already added")
            return

        if not Path(benchmark_file).exists():
            add_container.warning("File does not exists")
            return

        with open(benchmark_file, "r", encoding="utf-8") as fd:
            file_contents = json.load(fd)

        for benchmark in st.session_state["benchmarks"].values():
            if file_contents["uuid"] == benchmark["uuid"]:
                add_container.warning("Benchmark with the same uuid already exists")
                return

        st.session_state["benchmark_files"].append(benchmark_file)
        with open(benchmark_results_files, "w", encoding="utf-8") as fd:
            json.dump(list(st.session_state["benchmark_files"]), fd)
        st.session_state["benchmarks"][benchmark_file] = file_contents

        add_container.text(f"Added {benchmark_file} set")

    add_container.button("Add benchmark set from file", on_click=add_benchmark)

###############################################################################
# View tab
# Allows viewing existing benchmarks
###############################################################################

with view_tab:
    set_choice, benchmark_choice, compare = st.columns([3, 3, 1])

    sets = {
        f"{benchmark['name']} ({benchmark['uuid']})": benchmark
        for benchmark in st.session_state["benchmarks"].values()
    }
    benchmark_set = set_choice.selectbox("Benchmark set", sets.keys())

    if benchmark_set is None:
        set_choice.warning("No benchmark sets available")
        st.stop()

    selected_set = sets[benchmark_set]

    set_choice.text("Set description:")
    set_choice.markdown(selected_set["description"])

    benchmarks = {
        f"{benchmark['name']} ({benchmark['uuid']})": benchmark
        for benchmark in selected_set["benchmarks"].values()
    }

    benchmark = benchmark_choice.selectbox("Benchmark", benchmarks.keys())

    if benchmark is None:
        benchmark_choice.warning("No benchmarks in the set")
        st.stop()

    selected_benchmark = benchmarks[benchmark]

    benchmark_choice.text("Benchmark description:")
    benchmark_choice.markdown(selected_benchmark["description"])

    with st.expander("Benchmark stats"):
        reproducible_stats = {
            stat: selected_benchmark[stat]
            for stat in (
                "db_factory",
                "context_num",
                "from_dialog_len",
                "to_dialog_len",
                "step_dialog_len",
                "message_lengths",
                "misc_lengths",
            )
        }

        size_stats = {
            stat: naturalsize(selected_benchmark[stat], gnu=True)
            for stat in (
                "starting_context_size",
                "final_context_size",
                "misc_size",
                "message_size",
            )
        }

        st.json(reproducible_stats)
        st.json(size_stats)

    if not selected_benchmark["success"]:
        st.warning(selected_benchmark["result"])
    else:
        opposite_benchmark = None

        if st.session_state["partial_compare_checkbox"]:
            opposite_benchmarks = get_opposite_benchmarks(selected_set, selected_benchmark)

            if len(opposite_benchmarks) == 1:
                opposite_benchmark = opposite_benchmarks[0]

        add_metrics(st.container(), selected_benchmark, opposite_benchmark)

        if opposite_benchmark is not None:
            st.text(f"* In comparison with {opposite_benchmark['name']} ({opposite_benchmark['uuid']})")

        compare_item = {
            "benchmark_set": benchmark_set,
            "benchmark": benchmark,
            "write": selected_benchmark["average_results"]["pretty_write"],
            "read": selected_benchmark["average_results"]["pretty_read"],
            "update": selected_benchmark["average_results"]["pretty_update"],
            "read+update": selected_benchmark["average_results"]["pretty_read+update"],
        }

        def add_results_to_compare_tab():
            if compare_item not in st.session_state["compare"]:
                st.session_state["compare"].append(compare_item)
            else:
                st.session_state["compare"].remove(compare_item)

        compare.button(
            "Add to Compare" if compare_item not in st.session_state["compare"] else "Remove from Compare",
            on_click=add_results_to_compare_tab
        )

        select_graph, graph = st.columns([1, 3])

        graphs = {
            "Write": selected_benchmark["average_results"]["write_times"],
            "Read (grouped by contex_num)": selected_benchmark["average_results"]["read_times_grouped_by_context_num"],
            "Read (grouped by dialog_len)": selected_benchmark["average_results"]["read_times_grouped_by_dialog_len"],
            "Update (grouped by contex_num)": selected_benchmark["average_results"]["update_times_grouped_by_context_num"],
            "Update (grouped by dialog_len)": selected_benchmark["average_results"]["update_times_grouped_by_dialog_len"],
        }

        selected_graph = select_graph.selectbox("Select graph to display", graphs.keys())

        graph_data = graphs[selected_graph]

        if isinstance(graph_data, dict):
            data = pd.DataFrame({"dialog_len": graph_data.keys(), "time": graph_data.values()})
        else:
            data = pd.DataFrame({"context_num": range(len(graph_data)), "time": graph_data})

        chart = alt.Chart(data).mark_circle().encode(
            x="dialog_len:Q" if isinstance(graph_data, dict) else "context_num:Q",
            y="time:Q",
        ).interactive()

        graph.altair_chart(chart, use_container_width=True)


###############################################################################
# Compare tab
# Allows viewing existing benchmarks
###############################################################################

with compare_tab:
    df = pd.DataFrame(st.session_state["compare"])

    if not df.empty:
        st.dataframe(
            df.style.highlight_min(
                axis=0, subset=["write", "read", "update", "read+update"], props='background-color:green;'
            ).highlight_max(
                axis=0, subset=["write", "read", "update", "read+update"], props='background-color:red;'
            )
        )

        if len(st.session_state["compare"]) == 2:
            write, read, update, read_update = st.columns(4)

            first_dict, second_dict = st.session_state["compare"]

            columns = {
                "write": write,
                "read": read,
                "update": update,
                "read+update": read_update
            }

            for column_name, column in columns.items():
                column.metric(
                    label=column_name.title(),
                    value=f"{second_dict[column_name]}",
                    delta=get_diff(second_dict[column_name], first_dict[column_name]),
                    delta_color="inverse"
                )

###############################################################################
# Mass compare tab
# Allows massively comparing benchmarks inside a single set
###############################################################################

with mass_compare_tab:
    sets = {
        f"{benchmark['name']} ({benchmark['uuid']})": benchmark
        for benchmark in st.session_state["benchmarks"].values()
    }
    benchmark_set = st.selectbox("Benchmark set", sets.keys(), key="mass_compare_selectbox")

    if benchmark_set is None:
        st.warning("No benchmark sets available")
        st.stop()

    selected_set = sets[benchmark_set]

    added_benchmarks = set()

    for benchmark in selected_set["benchmarks"].values():
        if benchmark["uuid"] in added_benchmarks:
            continue

        opposite_benchmarks = get_opposite_benchmarks(selected_set, benchmark)

        added_benchmarks.add(benchmark["uuid"])
        added_benchmarks.update({bm["uuid"] for bm in opposite_benchmarks})
        st.divider()

        if len(opposite_benchmarks) == 1:
            opposite_benchmark = opposite_benchmarks[0]
            st.subheader(f"{benchmark['name']} ({benchmark['uuid']})")
            add_metrics(st.container(), benchmark, opposite_benchmark)
            st.subheader(f"{opposite_benchmark['name']} ({opposite_benchmark['uuid']})")
            add_metrics(st.container(), opposite_benchmark, benchmark)
