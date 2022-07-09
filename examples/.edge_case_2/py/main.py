from abc import global_flow, start_label

script = {
    global_flow: {
        start_label: {
            1: [1, 2],
        },
    },
    "global_flow": {
        2: [1, "2"],
    },
}

actor = Actor(start_label=("global_flow",), fallback_label=(global_flow, start_label), script=script)