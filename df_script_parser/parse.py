import libcst as cst
import typing as tp
import libcst.matchers as m
from .parse_utils import ImportBlock, evaluate
from pathlib import Path
import logging
from .processors import NodeProcessor


actor_matcher = m.Assign(value=m.Call(func=m.OneOf(m.Name("Actor"), m.Attribute(attr=m.Name("Actor")))))


class Parser(m.MatcherDecoratableTransformer):
    def __init__(self, path: tp.Union[str, Path], safe_mode: bool = True):
        super().__init__()
        self.path: tp.Union[str, Path] = path
        self.imports: ImportBlock = ImportBlock(working_dir=self.path, name="import.yaml")
        self.dict_node: tp.Optional[cst.Dict] = None
        self.args: tp.Dict[str, tp.Any] = {}
        self.safe_mode = safe_mode
        logging.debug(f"Created Parser with path={path}")

    @m.visit(m.Assign(value=m.Dict()))
    def add_dict(self, node: cst.Assign) -> None:
        """Save the dictionary node if the dictionary is being the target of an assignment."""
        self.dict_node = node.value

    @m.call_if_not_inside(m.Dict())
    @m.leave(actor_matcher)
    def parse_actor_args(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        """Parse arguments of calls to df_engine.core.Actor. Store them in self.args. Process saved dict."""
        actor_arg_order = (
            "script",
            "start_label",
            "fallback_label",
            "label_priority",
            "validation_stage",
            "condition_handler",
            "verbose",
            "handlers",
        )
        if isinstance(updated_node.value, cst.Call):
            for arg, keyword in zip(updated_node.value.args, actor_arg_order):
                if arg.keyword is not None:
                    keyword = evaluate(arg.keyword)
                self.args[keyword] = NodeProcessor(
                    arg.value, list(self.imports), parse_tuples=True, safe_mode=self.safe_mode
                ).result
                logging.info(f"Found arg {keyword} = {self.args[keyword]}")
        return updated_node

    @m.leave(m.Import() | m.ImportFrom())
    def add_import_to_structure(
        self,
        original_node: tp.Union[cst.Import, cst.ImportFrom],
        updated_node: tp.Union[cst.Import, cst.ImportFrom],
    ) -> tp.Union[cst.Import, cst.ImportFrom]:
        """Add import statement block to the self.structure."""
        self.imports.append(updated_node)
        return updated_node
