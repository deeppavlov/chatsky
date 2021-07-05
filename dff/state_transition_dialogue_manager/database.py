from structpy.graph.labeled_digraph import MapMultidigraph


class GraphDatabase(MapMultidigraph):
    def __init__(self, arcs=None):
        MapMultidigraph.__init__(self)
        self._node_data = {n: {} for n in self.nodes()}
        self._arc_data = {(s, t, l): {} for s, t, l in self.arcs()}
        if arcs is not None:
            for arc in arcs:
                self.add(*arc)

    def add_node(self, node):
        MapMultidigraph.add_node(self, node)
        self._node_data[node] = {}

    def add_arc(self, source, target, label=None):
        if label is None:
            MapMultidigraph.add_arc(self, source, target)
        else:
            MapMultidigraph.add_arc(self, source, target, label)
        self._arc_data[(source, target, label)] = {}

    def remove_node(self, node):
        MapMultidigraph.remove_node(self, node)
        del self._node_data[node]

    def remove_arc(self, source, target):
        MapMultidigraph.remove_arc(self, source, target)
        del self._arc_data[(source, target)]

    def data(self, node):
        return self._node_data[node]

    def arc_data(self, source, target, label=None):
        if label is None:
            label = MapMultidigraph.label(self, source, target)
        return self._arc_data[(source, target, label)]

    def update(self, other):
        MapMultidigraph.update(self, other)
        if hasattr(other, "_node_data"):
            self._node_data.update(other._node_data)
            if hasattr(other, "_arc_data"):
                self._arc_data.update(other._arc_data)
