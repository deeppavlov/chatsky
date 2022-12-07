from pathlib import Path
import builtins

from .base_parser_object import *
from .namespace import Namespace
from .exceptions import ScriptValidationError
from .yaml import yaml, python_factory as yaml_python_factory
from dff.core.engine.core.actor import Actor
from dff.core.engine.core.keywords import Keywords


logger = logging.getLogger(__name__)


ScriptInitializers = {
    "dff.core.engine.core.Actor": Actor.__init__.__wrapped__.__code__.co_varnames[1:],
    "dff.core.engine.core.actor.Actor": Actor.__init__.__wrapped__.__code__.co_varnames[1:],
}

keywords_dict = {
    k: ["dff.core.engine.core.keywords." + k, "dff.core.engine.core.keywords.Keywords." + k]
    for k in Keywords.__members__
}

keywords_list = list(map(lambda x: "dff.core.engine.core.keywords." + x, Keywords.__members__)) + list(
    map(lambda x: "dff.core.engine.core.keywords.Keywords." + x, Keywords.__members__)
)


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
                        if func_name in ScriptInitializers.keys():
                            if call is None:
                                call = value
                            else:
                                raise ScriptValidationError(f"Found two Actor calls\nFirst: {str(call)}\nSecond:{str(value)}")
        if call is not None:
            return call
        raise ScriptValidationError("Actor call is not found")

    @cached_property
    def script(self) -> tp.Tuple[Expression, Expression, tp.Optional[Expression]]:
        call = self.actor_call
        args = {}
        func = call.resolve_path(("func", ))
        func_name = str(func.resolve_name)
        for index, arg in enumerate(ScriptInitializers[func_name]):
            args[arg] = call.children.get("arg_" + str(index)) or call.children.get("keyword_" + arg)
        if args["script"] is None:
            raise ScriptValidationError(f"Actor argument `script` is not found: {str(call)}")
        if args["start_label"] is None:
            raise ScriptValidationError(f"Actor argument `start_label` is not found: {str(call)}")
        return args["script"], args["start_label"], args["fallback_label"]

    @cached_property
    def resolved_script(self) -> dict:
        """

        :return: Resolved script
        """
        script = defaultdict(dict)

        def resolve(obj: BaseParserObject) -> BaseParserObject:
            if isinstance(obj, ReferenceObject):
               if obj.absolute is not None:
                   return obj.absolute
            return obj

        def resolve_node(node_info: Expression) -> dict:
            result = {}
            node_info = resolve(node_info)
            if not isinstance(node_info, Dict):
                raise ScriptValidationError(f"Node {str(node_info)} is not a Dict")
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
                result[resolve(key)] = resolve(value)
            return result

        flows = resolve(self.script[0])
        if not isinstance(flows, Dict):
            raise ScriptValidationError(f"{str(self.script[0])} is not a Dict: {str(flows)}")
        for flow, nodes in flows.items():
            if flow in keywords_dict["GLOBAL"]:
                script[resolve(flow)] = resolve_node(nodes)
            else:
                nodes = resolve(nodes)
                if not isinstance(nodes, Dict):
                    raise ScriptValidationError(f"{str(self.script[0])} is not a Dict: {str(flows)}")
                for node, info in nodes.items():
                    script[resolve(flow)][resolve(node)] = resolve_node(info)
        return script

    def to_dict(
        self,
        str_factory: tp.Callable[[BaseParserObject], object],
        python_factory: tp.Callable[[BaseParserObject], object],
        object_filter: tp.Dict[str, tp.Set[str]],
    ) -> dict:

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
                try:
                    parsed = ast.parse(bpo.string).body
                    if len(parsed) != 1:
                        return bpo.string
                    parsed_expr = parsed[0]
                    if not isinstance(parsed_expr, ast.Expr):
                        return bpo.string

                    expr = Expression.from_ast(parsed_expr.value)
                    if expr.names <= allowed_objects:  # dependencies alone are not enough to differ between str and python
                        return str_factory(bpo)
                    else:
                        return bpo.string
                except SyntaxError:  # string is not a valid python node
                    return bpo.string
            if isinstance(bpo, Expression):
                if bpo.names <= allowed_objects:
                    return str(bpo)
                else:
                    return python_factory(bpo)
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
            yaml.dump(self.to_dict(str, yaml_python_factory, self.actor_call.dependencies), fd)
