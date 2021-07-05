from dff.state_transition_dialogue_manager.database import GraphDatabase as Graph
from structpy.graph.traversal import preset as traversal

# from dff.state_transition_dialogue_manager.utilities import lemmatize_ontology
import json
from collections import defaultdict
import regex

_type = "type"
_attr = "attr"
_expr = "expr"

_expr_regex = r"[a-z A-Z0-9,]+"


class KnowledgeBase(Graph):
    def __init__(self, arcs=None):
        Graph.__init__(self)
        if arcs is not None:
            for s, r, o in arcs:
                self.add_relation(s, r, o)

    def query(self, node, *relations):
        if isinstance(node, set):
            result_set = set().union(node)
        else:
            result_set = {node}
        for relation_set in relations:
            new_result_set = set()
            if not isinstance(relation_set, set):
                relation_set = {relation_set}
            for relation in relation_set:
                if relation == "*":
                    for n in result_set:
                        new_result_set.update({x[1] for x in self.arcs_out(n)})
                elif relation[0] == "~":
                    relation = relation[1:]
                    for n in result_set:
                        if self.has_arc_label(n, relation):
                            new_result_set.update({x[0] for x in self.arcs_in(n, relation)})
                else:
                    for n in result_set:
                        if self.has_arc_label(n, relation):
                            new_result_set.update({x[1] for x in self.arcs_out(n, relation)})
            result_set = new_result_set
        return result_set

    def add_type(self, subtype, type):
        self.add(subtype, type, _type)
        if regex.fullmatch(_expr_regex, type):
            self.add(type, type, _expr)
        if regex.fullmatch(_expr_regex, subtype):
            self.add(subtype, subtype, _expr)

    def add_relation(self, subject, relation, object):
        self.add(subject, object, relation)
        if regex.fullmatch(_expr_regex, subject):
            self.add(subject, subject, _expr)
        if regex.fullmatch(_expr_regex, object):
            self.add(object, object, _expr)

    def add_expression(self, node, expression):
        self.add(node, expression, _expr)
        if regex.fullmatch(_expr_regex, node):
            self.add(node, node, _expr)

    def add_attr(self, type, attribute):
        if _attr not in self.data(type):
            self.data(type)[_attr] = set()
        self.data(type)[_attr].add(attribute)

    def types(self, node_set):
        if not isinstance(node_set, set):
            node_set = {node_set}
        types = set()
        for node in node_set:
            if self.has_node(node):
                s = set(traversal.BreadthFirstOnArcs(self, node, _type)) - {node}
                types.update(s)
        return types

    def subtypes(self, node_set):
        if not isinstance(node_set, set):
            node_set = {node_set}
        subtypes = set()
        for node in node_set:
            if self.has_node(node):
                subtypes.update(set(traversal.BreadthFirstOnArcsReverse(self, node, _type)))
        return subtypes

    def expressions(self, node_set):
        if not isinstance(node_set, set):
            node_set = {node_set}
        expressions = set()
        for node in node_set:
            if self.has_arc_label(node, _expr):
                expressions.update({x[1] for x in self.arcs_out(node, _expr)})
        return expressions

    def to_json(self):
        ontology_arcs = defaultdict(list)
        expression_arcs = defaultdict(list)
        relation_arcs = list()
        for s, o, r in self.arcs():
            if r == _type:
                ontology_arcs[o].append(s)
            elif r == _expr:
                expression_arcs[s].append(o)
            else:
                relation_arcs.append([s, r, o])
        return json.dumps(
            {
                "ontology": ontology_arcs,
                "predicates": relation_arcs,
                "expressions": expression_arcs,
            },
            indent=4,
            sort_keys=True,
        )

    def load_json_file(self, json_file, lemmatize=False):
        f = open(json_file, "r")
        d = json.load(f)
        self.load_json(d, lemmatize)

    def load_json_string(self, json_string, lemmatize=False):
        d = json.loads(json_string)
        self.load_json(d, lemmatize)

    def load_json(self, d, lemmatize=False):
        if "ontology" in d:
            # if lemmatize:
            #     ontology = lemmatize_ontology(d['ontology'])
            # else:
            #     ontology = d['ontology']
            ontology = d["ontology"]
            for k, l in ontology.items():
                for e in l:
                    self.add_type(e, k)
        if "predicates" in d:
            relations = d["predicates"]
            for relation in relations:
                s, r, o = tuple(relation)
                self.add_relation(s, r, o)
        if "expressions" in d:
            expressions = d["expressions"]
            for n, l in expressions.items():
                for e in l:
                    self.add_expression(n, e)
