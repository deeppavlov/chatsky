from pathlib import Path
import builtins
import json

try:
    import networkx as nx
except ImportError:
    raise ImportError(f"Module `networkx` is not installed. Install it with `pip install dff[parser]`.")

from .base_parser_object import *
from .namespace import Namespace
from .exceptions import ScriptValidationError
from .yaml import yaml
from dff.core.engine.core.actor import Actor
from dff.core.engine.core.keywords import Keywords
from dff.core.engine.labels import forward, backward


logger = logging.getLogger(__name__)


script_initializers = {
    "dff.core.engine.core.Actor": Actor.__init__.__wrapped__.__code__.co_varnames[1:],
    "dff.core.engine.core.actor.Actor": Actor.__init__.__wrapped__.__code__.co_varnames[1:],
}

labels = {
    "dff.core.engine.labels.forward": forward.__code__.co_varnames[:2],
    "dff.core.engine.labels.backward": backward.__code__.co_varnames[:2],
}

keywords_dict = {
    k: ["dff.core.engine.core.keywords." + k, "dff.core.engine.core.keywords.Keywords." + k]
    for k in Keywords.__members__
}

keywords_list = list(map(lambda x: "dff.core.engine.core.keywords." + x, Keywords.__members__)) + list(
    map(lambda x: "dff.core.engine.core.keywords.Keywords." + x, Keywords.__members__)
)

reversed_keywords_dict = {
    prefix + k: k for k in Keywords.__members__ for prefix in ("dff.core.engine.core.keywords.", "dff.core.engine.core.keywords.Keywords.")
}


class DFFProject(BaseParserObject):
    def __init__(self, namespaces: tp.List['Namespace']):
        super().__init__()
        self.children: tp.Dict[str, Namespace]
        for namespace in namespaces:
            self.add_child(namespace, namespace.name)

    @cached_property
    def actor_call(self) -> Call:
        call = None
        for namespace in self.children.values():
            for statement in namespace.children.values():
                if isinstance(statement, Assignment):
                    value = statement.children["value"]
                    if isinstance(value, Call):
                        func = value.resolve_path(("func", ))
                        func_name = str(func.resolve_name)
                        if func_name in script_initializers.keys():
                            if call is None:
                                call = value
                            else:
                                raise ScriptValidationError(f"Found two Actor calls\nFirst: {str(call)}\nSecond:{str(value)}")
        if call is not None:
            return call
        raise ScriptValidationError("Actor call is not found")

    @cached_property
    def script(self) -> tp.Tuple[Expression, tp.Tuple[Expression, Expression], tp.Tuple[Expression, Expression]]:
        call = self.actor_call
        args: tp.Dict[str, tp.Optional[Expression]] = call.get_args(script_initializers[call.func_name])
        script = args.get("script")
        start_label = args.get("start_label")
        fallback_label = args.get("fallback_label")

        # script validation
        if script is None:
            raise ScriptValidationError(f"Actor argument `script` is not found: {str(call)}")

        # start_label validation
        if start_label is None:
            raise ScriptValidationError(f"Actor argument `start_label` is not found: {str(call)}")
        label = start_label
        if isinstance(label, ReferenceObject):
            label = label.absolute
        if not isinstance(label, Iterable):
            raise ScriptValidationError(f"Start label {start_label} resolves to {label} which is not iterable.")
        if len(label) != 2:
            raise ScriptValidationError(f"Length of start label should be 2: {label}")
        if not isinstance(label[0].resolve, String) or not isinstance(label[1].resolve, String):
            raise ScriptValidationError(f"Label element should be strings: {label}")
        start_label = (str(label[0].resolve), str(label[1].resolve))

        # fallback_label validation
        if fallback_label is None:
            fallback_label = start_label
        else:
            label = fallback_label
            if isinstance(label, ReferenceObject):
                label = label.absolute
            if not isinstance(label, Iterable):
                raise ScriptValidationError(f"Start label {fallback_label} resolves to {label} which is not iterable.")
            if len(label) != 2:
                raise ScriptValidationError(f"Length of start label should be 2: {label}")
            if not isinstance(label[0].resolve, String) or not isinstance(label[1].resolve, String):
                raise ScriptValidationError(f"Label element should be strings: {label}")
            fallback_label = (str(label[0].resolve), str(label[1].resolve))

        return script, start_label, fallback_label

    @cached_property
    def resolved_script(self) -> tp.Dict[BaseParserObject, tp.Dict[BaseParserObject, tp.Dict[str, BaseParserObject]]]:
        """

        :return: Resolved script
        """
        script = defaultdict(dict)

        def resolve_node(node_info: Expression) -> tp.Dict[str, BaseParserObject]:
            result = {}
            node_info = node_info.resolve
            if not isinstance(node_info, Dict):
                raise ScriptValidationError(f"Node {str(node_info)} is not a Dict")
            result["__node__"] = node_info
            for key, value in node_info.items():
                str_key = str(key)
                if isinstance(key, ReferenceObject):
                    str_key = str(key.resolve_name)
                if str_key not in keywords_list:
                    raise ScriptValidationError(f"Node key {str_key} is not a keyword")
                if str_key in keywords_dict["GLOBAL"]:
                    raise ScriptValidationError(f"Node key is a GLOBAL keyword: {str_key}")
                if str_key in keywords_dict["LOCAL"]:
                    raise ScriptValidationError(f"Node key is a LOCAL keyword: {str_key}")

                keyword = reversed_keywords_dict[str_key]

                if result.get(keyword) is not None:  # duplicate found
                    raise ScriptValidationError(f"Keyword {str_key} is used twice in one node: {str(node_info)}")

                result[reversed_keywords_dict[str_key]] = value.resolve
            return result

        flows = self.script[0].resolve
        if not isinstance(flows, Dict):
            raise ScriptValidationError(f"{str(self.script[0])} is not a Dict: {str(flows)}")
        for flow, nodes in flows.items():
            if flow in keywords_dict["GLOBAL"]:
                script[flow.resolve][None] = resolve_node(nodes)
            else:
                nodes = nodes.resolve
                if not isinstance(nodes, Dict):
                    raise ScriptValidationError(f"{str(self.script[0])} is not a Dict: {str(flows)}")
                for node, info in nodes.items():
                    script[flow.resolve][node.resolve] = resolve_node(info)

        # validate labels
        for label in self.script[1:3]:
            flow = script.get(label[0])
            if flow is None:
                raise ScriptValidationError(f"Not found flow {str(label[0])} in {[str(key) for key in script.keys()]}")
            else:
                if flow.get(label[1]) is None:
                    raise ScriptValidationError(f"Not found node {str(label[1])} in {[str(key) for key in script.keys()]}")

        return script

    @cached_property
    def graph(self) -> nx.MultiDiGraph:
        def resolve_label(label: Expression, current_flow: Expression) -> tuple:
            if isinstance(label,  ReferenceObject):  # label did not resolve (possibly due to a missing func def)
                return ("NONE", )
            if isinstance(label, String):
                return (str(current_flow), str(label))  # maybe shouldn't use str on String
            if isinstance(label, Iterable):
                if not isinstance(label[0].resolve, String):
                    raise ScriptValidationError(f"First argument of label is not str: {label}")
                if len(label) == 2 and not isinstance(label[1].resolve, String):  # todo: add type check for label[1]
                    return (str(current_flow), str(label[0].resolve))
                if len(label) == 2:
                    return (str(label[0].resolve), str(label[1].resolve))
                if len(label) == 3:
                    if not isinstance(label[1].resolve, String):
                        raise ScriptValidationError(f"Second argument of label is not str: {label}")
                    return (str(label[0].resolve), str(label[1].resolve))
            if isinstance(label, Call):
                if label.func_name == 'dff.core.engine.labels.repeat':
                    return ("REPEAT",)
                if label.func_name == 'dff.core.engine.labels.previous':
                    return ("PREVIOUS",)
                if label.func_name == 'dff.core.engine.labels.to_start':
                    return ("START",)
                if label.func_name == 'dff.core.engine.labels.to_fallback':
                    return ("FALLBACK",)
                if label.func_name == 'dff.core.engine.labels.to_start':
                    return ("START",)
                if label.func_name == 'dff.core.engine.labels.forward':
                    return (f"FORWARD_cyclicality={str(label.get_args(labels[label.func_name]).get('cyclicality_flag') or True)}",)
                if label.func_name == 'dff.core.engine.labels.backward':
                    return (f"BACKWARD_cyclicality={str(label.get_args(labels[label.func_name]).get('cyclicality_flag') or True)}",)
            logger.warning(f'Label did not resolve: {label}')
            return ("NONE",)
        graph = nx.MultiDiGraph(full_script=self.to_dict(self.actor_call.dependencies, False), start_label=self.script[1], fallback_label=self.script[2])
        for flow_name, flow in self.resolved_script.items():
            for node_name, node_info in flow.items():
                current_label = (str(flow_name), str(node_name)) if node_name is not None else (str(flow_name), )
                graph.add_node(
                    current_label,
                    ref=node_info["__node__"].path,
                    local=node_name in keywords_dict["LOCAL"],
                )
                transitions = node_info.get("TRANSITIONS")
                if transitions is None:
                    continue
                if not isinstance(transitions, Dict):
                    raise ScriptValidationError(f"TRANSITIONS keyword should point to a dictionary: {transitions}")
                for label, condition in transitions.items():
                    graph.add_edge(
                        current_label,
                        resolve_label(label.resolve, flow_name),
                        label_ref=label.resolve.path,
                        label=str(label.resolve),
                        condition_ref=condition.resolve.path,
                        condition=str(condition.resolve)
                    )
        return graph

    def to_dict(
        self,
        object_filter: tp.Dict[str, tp.Set[str]],
        validate: bool = True,
    ) -> dict:
        if validate:
            _ = self.resolved_script

        def process_base_parser_object(bpo: BaseParserObject):
            allowed_objects = set(object_filter[bpo.namespace.name])
            allowed_objects.update(set(builtins.__dict__.keys()))

            if isinstance(bpo, Assignment):
                return process_base_parser_object(bpo.children["value"])
            if isinstance(bpo, Import):
                return f"import {bpo.module}"
            if isinstance(bpo, ImportFrom):
                return f"from {bpo.level * '.' + bpo.module} import {bpo.obj}"
            if isinstance(bpo, Dict):
                processed_dict = {}
                for key, value in bpo.items():
                    processed_dict[process_base_parser_object(key)] = process_base_parser_object(value)
                return processed_dict
            if isinstance(bpo, String):
                return str(bpo)
            if isinstance(bpo, Expression):
                return str(bpo)
            raise TypeError(str(type(bpo)) + "_" + repr(bpo))

        result = defaultdict(dict)
        for namespace_name, namespace in self.children.items():
            namespace_filter = object_filter.get(namespace_name)
            if namespace_filter is not None:
                for obj_name, obj in namespace.children.items():
                    if obj_name in namespace_filter:
                        result[namespace_name][obj_name] = process_base_parser_object(obj)
        return dict(result)

    def __getitem__(self, item: tp.Union[tp.List[str], str]) -> Namespace:
        if isinstance(item, str):
            return self.children[item]
        elif isinstance(item, list):
            if item[-1] == "__init__":
                return self.children[".".join(item)]
            namespace = self.children.get(".".join(item))
            if namespace is None:
                return self.children[".".join(item) + ".__init__"]
            return namespace
        raise TypeError(f"{type(item)}")

    @cached_property
    def path(self) -> tp.Tuple[str, ...]:
        return ()

    @cached_property
    def namespace(self) -> 'Namespace':
        raise RuntimeError(f"DFFProject does not have a `namespace` attribute\n{repr(self)}")

    @cached_property
    def dff_project(self) -> 'DFFProject':
        return self

    def __str__(self) -> str:
        return "\n".join(map(str, self.children.values()))

    def __repr__(self) -> str:
        return f"DFFProject({'; '.join(map(repr, self.children.values()))})"

    @classmethod
    def from_ast(cls, node, **kwargs):
        raise NotImplementedError()

    @classmethod
    def from_python(cls, project_root_dir: Path, entry_point: Path):
        namespaces = {}
        if not project_root_dir.exists():
            raise RuntimeError(f"Path does not exist: {project_root_dir}")

        def _process_file(file: Path):
            if not file.exists():
                raise RuntimeError(f"File {file} does not exist in {project_root_dir}")
            namespace = Namespace.from_file(project_root_dir, file)
            namespaces[namespace.name] = namespace

            for imported_file in namespace.get_imports():
                if ".".join(imported_file) not in namespaces.keys():
                    path = project_root_dir.joinpath(*imported_file).with_suffix(".py")
                    if path.exists():
                        _process_file(path)

        _process_file(entry_point)
        return cls(list(namespaces.values()))

    def to_yaml(self, file: Path):
        with open(file, "w", encoding="utf-8") as fd:
            yaml.dump(self.to_dict(self.actor_call.dependencies), fd)

    def to_graph(self, file: Path):
        with open(file, "w", encoding="utf-8") as fd:
            json.dump(nx.readwrite.node_link_data(self.graph), fd, indent=4)
