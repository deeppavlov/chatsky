import streamlit as st
import json
from pathlib import Path
from statistics import mean
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


def get_opposite_benchmark(benchmark_set, benchmark):
    compare_params = (
        ["db_factory", "uri"],
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

    if len(opposite_benchmarks) == 1:
        return opposite_benchmarks[0]
    else:
        return None


def set_average_results(benchmark):
    if not benchmark["success"] or isinstance(benchmark["result"], str):
        return

    if benchmark.get("average_results") is not None:
        return

    def get_complex_stats(results):
        average_grouped_by_context_num = [mean(times.values()) for times in results]
        average_grouped_by_dialog_len = {key: mean([times[key] for times in results]) for key in results[0].keys()}
        average = mean(average_grouped_by_context_num)
        return average_grouped_by_context_num, average_grouped_by_dialog_len, average

    read_stats = get_complex_stats(benchmark["result"]["read_times"])
    update_stats = get_complex_stats(benchmark["result"]["update_times"])

    result = {
        "average_write_time": mean(benchmark["result"]["write_times"]),
        "average_read_time": read_stats[2],
        "average_update_time": update_stats[2],
        "write_times": benchmark["result"]["write_times"],
        "read_times_grouped_by_context_num": read_stats[0],
        "read_times_grouped_by_dialog_len": read_stats[1],
        "update_times_grouped_by_context_num": update_stats[0],
        "update_times_grouped_by_dialog_len": update_stats[1],
    }
    result["pretty_write"] = float(f'{result["average_write_time"]:.3}')
    result["pretty_read"] = float(f'{result["average_read_time"]:.3}')
    result["pretty_update"] = float(f'{result["average_update_time"]:.3}')

    benchmark["average_results"] = result


st.sidebar.text(f"Benchmarks take {naturalsize(asizeof.asizeof(st.session_state['benchmarks']))} RAM")

st.sidebar.divider()

st.sidebar.checkbox("Compare dev and partial in view tab", value=True, key="partial_compare_checkbox")
st.sidebar.checkbox("Percent comparison", value=True, key="percent_compare")

add_tab, view_tab, compare_tab = st.tabs(["Benchmark sets", "View", "Compare"])


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
        set_average_results(selected_benchmark)

        diffs = None
        if st.session_state["partial_compare_checkbox"]:
            opposite_benchmark = get_opposite_benchmark(selected_set, selected_benchmark)

            if opposite_benchmark:
                if not opposite_benchmark["success"]:
                    diffs = {
                        "write": "-",
                        "read": "-",
                        "update": "-",
                    }
                else:
                    set_average_results(opposite_benchmark)
                    diffs = {
                        key: get_diff(
                            selected_benchmark["average_results"][f"pretty_{key}"],
                            opposite_benchmark["average_results"][f"pretty_{key}"]
                        ) for key in ("write", "read", "update")
                    }

        write, read, update = st.columns(3)

        columns = {
            "write": write,
            "read": read,
            "update": update,
        }

        for column_name, column in columns.items():
            column.metric(
                column_name.title(),
                selected_benchmark["average_results"][f"pretty_{column_name}"],
                delta=diffs[column_name] if diffs else None,
                delta_color="inverse"
            )

        if diffs:
            st.text(f"* In comparison with {opposite_benchmark['name']} ({opposite_benchmark['uuid']})")

        compare_item = {
            "benchmark_set": benchmark_set,
            "benchmark": benchmark,
            "write": selected_benchmark["average_results"]["average_write_time"],
            "read": selected_benchmark["average_results"]["average_read_time"],
            "update": selected_benchmark["average_results"]["average_update_time"],
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
                axis=0, subset=["write", "read", "update"], props='background-color:green;'
            ).highlight_max(
                axis=0, subset=["write", "read", "update"], props='background-color:red;'
            )
        )

        if len(st.session_state["compare"]) == 2:
            write, read, update = st.columns(3)

            first_dict, second_dict = st.session_state["compare"]

            columns = {
                "write": write,
                "read": read,
                "update": update,
            }

            for column_name, column in columns.items():
                column.metric(
                    label=column_name.title(),
                    value=f"{second_dict[column_name]:.3}",
                    delta=get_diff(second_dict[column_name], first_dict[column_name]),
                    delta_color="inverse"
                )
