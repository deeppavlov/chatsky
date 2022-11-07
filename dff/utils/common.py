from logging import Logger
from typing import Optional, Tuple, Dict, Union, Hashable

from dff.connectors.db import DBAbstractConnector
from dff.core.engine.core import Actor
from dff.core.pipeline import Pipeline, ServiceBuilder
from dff.utils.messenger_interface import LoggerMessengerInterface
from dff.utils.toy_script import TOY_SCRIPT, HAPPY_PATH


def is_in_notebook() -> bool:
    shell = None
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
    finally:
        return shell == "ZMQInteractiveShell"


def create_example_actor(
    toy_script: Optional[Dict] = None,
    start_label: Optional[Tuple[str, str]] = None,
    fallback_label: Optional[Tuple[str, str]] = None,
) -> Actor:
    toy_script = TOY_SCRIPT if toy_script is None else toy_script
    start_label = ("greeting_flow", "start_node") if start_label is None else start_label
    fallback_label = ("greeting_flow", "fallback_node") if fallback_label is None else fallback_label
    return Actor(toy_script, start_label, fallback_label)


def create_example_pipeline(
    logger: Optional[Logger] = None,
    happy_path: Optional[Tuple[Tuple[str, str], ...]] = None,
    actor: Optional[Actor] = None,
    pipeline: Optional[Pipeline] = None,
    toy_script: Optional[Dict] = None,
    start_label: Optional[Tuple[str, str]] = None,
    fallback_label: Optional[Tuple[str, str]] = None,
    context_id: Optional[Hashable] = None,
    context_storage: Optional[Union[DBAbstractConnector, Dict]] = None,
    request_wrapper: Optional[ServiceBuilder] = None,
    response_wrapper: Optional[ServiceBuilder] = None
) -> Pipeline:
    if happy_path is None and is_in_notebook():
        happy_path = HAPPY_PATH
    messenger_interface = LoggerMessengerInterface(logger, context_id, happy_path)

    if actor is None:
        actor = create_example_actor(toy_script, start_label, fallback_label)
    elif toy_script is not None or start_label is not None or fallback_label is not None:
        raise Exception("Script, start node or fallback node can't be changed for existing actor!!")

    context_storage = dict() if context_storage is None else context_storage
    pre_services = None if request_wrapper is None else [request_wrapper]
    post_services = None if response_wrapper is None else [response_wrapper]

    if pipeline is None:
        pipeline = Pipeline.from_script(
            actor.script,
            actor.start_label[:2],
            actor.fallback_label[:2],
            context_storage,
            messenger_interface,
            pre_services,
            post_services
        )
    else:
        pipeline.actor = actor
        pipeline.context_storage = context_storage
        pipeline.messenger_interface = messenger_interface
        if request_wrapper is not None or response_wrapper is not None:
            raise Exception("Request or response wrappers can't be added to existing pipeline!!")

    return pipeline


def run_example(logger: Optional[Logger] = None, **kwargs):
    create_example_pipeline(logger, **kwargs).run()
