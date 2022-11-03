from dff.core.engine.core.keywords import TRANSITIONS as tr
import consts

d = {
    1: "flow",
    2: {
        3: "node2",
    },
}

ints = {3: 3}

here = {("flow2", "node1"): print("cond")}

node = {
    tr: {
        ("flow", "node1"): print("cnd"),
        (d[1], d[2][ints[3]]): consts.conds[1],
        consts.there[ints[3]]: here[consts.there[ints[3]]],
    }
}
