"""
Pipeline
--------
The Pipeline module contains the :py:class:`.Pipeline` class,
which is a fundamental element of the DFF. The Pipeline class is responsible
for managing and executing the various components (:py:class:`.PipelineComponent`)which make up
the processing of messages from and to users.
It provides a way to organize and structure the messages processing flow.
The Pipeline class is designed to be highly customizable and configurable,
allowing developers to add, remove, or modify the components that make up the messages processing flow.

The Pipeline class is designed to be used in conjunction with the :py:class:`.PipelineComponent`
class, which is defined in the Component module. Together, these classes provide a powerful and flexible way
to structure and manage the messages processing flow.
"""
import asyncio
import logging
from typing import Union, List, Dict, Optional, Hashable, Callable

from dff.context_storages import DBContextStorage
from dff.script import Script, Context, ActorStage
from dff.script import NodeLabel2Type, Message
from dff.utils.turn_caching import cache_clear

from dff.messengers.common import MessengerInterface, CLIMessengerInterface
from ..service.group import ServiceGroup
from ..types import (
    ServiceBuilder,
    ServiceGroupBuilder,
    PipelineBuilder,
    GlobalExtraHandlerType,
    ExtraHandlerFunction,
    ExtraHandlerBuilder,
)
from ..types import PIPELINE_STATE_KEY
from .utils import finalize_service_group, pretty_format_component_info_dict
from dff.pipeline.pipeline.actor import Actor

logger = logging.getLogger(__name__)

ACTOR = "ACTOR"


class Pipeline:
    """
    Class that automates service execution and creates service pipeline.
    It accepts constructor parameters:

    :param script: (required) A :py:class:`~.Script` instance (object or dict).
    :param start_label: (required) Actor start label.
    :param fallback_label: Actor fallback label.
    :param label_priority: Default priority value for all actor :py:const:`labels <dff.script.NodeLabel3Type>`
        where there is no priority. Defaults to `1.0`.
    :param validation_stage: This flag sets whether the validation stage is executed after actor creation.
        It is executed by default. Defaults to `None`.
    :param condition_handler: Handler that processes a call of actor condition functions. Defaults to `None`.
    :param verbose: If it is `True`, logging is used in actor. Defaults to `True`.
    :param handlers: This variable is responsible for the usage of external handlers on
        the certain stages of work of :py:class:`~dff.script.Actor`.

        - key: :py:class:`~dff.script.ActorStage` - Stage in which the handler is called.
        - value: List[Callable] - The list of called handlers for each stage. Defaults to an empty `dict`.

    :param messenger_interface: An `AbsMessagingInterface` instance for this pipeline.
    :param context_storage: An :py:class:`~.DBContextStorage` instance for this pipeline or
        a dict to store dialog :py:class:`~.Context`.
    :param services: (required) A :py:data:`~.ServiceGroupBuilder` object,
        that will be transformed to root service group. It should include :py:class:`~.Actor`,
        but only once (raises exception otherwise). It will always be named pipeline.
    :param wrappers: List of wrappers to add to pipeline root service group.
    :param timeout: Timeout to add to pipeline root service group.
    :param optimization_warnings: Asynchronous pipeline optimization check request flag;
        warnings will be sent to logs. Additionally it has some calculated fields:

        - `_services_pipeline` is a pipeline root :py:class:`~.ServiceGroup` object,
        - `actor` is a pipeline actor, found among services.

    """

    def __init__(
        self,
        components: ServiceGroupBuilder,
        script: Union[Script, Dict],
        start_label: NodeLabel2Type,
        fallback_label: Optional[NodeLabel2Type] = None,
        label_priority: float = 1.0,
        validation_stage: Optional[bool] = None,
        condition_handler: Optional[Callable] = None,
        verbose: bool = True,
        handlers: Optional[Dict[ActorStage, List[Callable]]] = None,
        messenger_interface: Optional[MessengerInterface] = None,
        context_storage: Optional[Union[DBContextStorage, Dict]] = None,
        before_handler: Optional[ExtraHandlerBuilder] = None,
        after_handler: Optional[ExtraHandlerBuilder] = None,
        timeout: Optional[float] = None,
        optimization_warnings: bool = False,
    ):
        self.actor: Actor = None
        self.messenger_interface = CLIMessengerInterface() if messenger_interface is None else messenger_interface
        self.context_storage = {} if context_storage is None else context_storage
        self._services_pipeline = ServiceGroup(
            components,
            before_handler=before_handler,
            after_handler=after_handler,
            timeout=timeout,
        )

        self._services_pipeline.name = "pipeline"
        self._services_pipeline.path = ".pipeline"
        actor_exists = finalize_service_group(self._services_pipeline, path=self._services_pipeline.path)
        if not actor_exists:
            raise Exception("Actor not found in pipeline!")
        else:
            self.set_actor(
                script,
                start_label,
                fallback_label,
                label_priority,
                validation_stage,
                condition_handler,
                verbose,
                handlers,
            )
        if self.actor is None:
            raise Exception("Actor wasn't initialized correctly!")

        if optimization_warnings:
            self._services_pipeline.log_optimization_warnings()

        # NB! The following API is highly experimental and may be removed at ANY time WITHOUT FURTHER NOTICE!!
        self._clean_turn_cache = True
        if self._clean_turn_cache:
            self.actor._clean_turn_cache = False

    def add_global_handler(
        self,
        global_handler_type: GlobalExtraHandlerType,
        extra_handler: ExtraHandlerFunction,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ):
        """
        Method for adding global wrappers to pipeline.
        Different types of global wrappers are called before/after pipeline execution
        or before/after each pipeline component.
        They can be used for pipeline statistics collection or other functionality extensions.
        NB! Global wrappers are still wrappers,
        they shouldn't be used for much time-consuming tasks (see ../service/wrapper.py).

        :param global_handler_type: (required) indication where the wrapper
            function should be executed.
        :param extra_handler: (required) wrapper function itself.
        :type extra_handler: ExtraHandlerFunction
        :param whitelist: a list of services to only add this wrapper to.
        :param blacklist: a list of services to not add this wrapper to.
        :return: `None`
        """

        def condition(name: str) -> bool:
            return (whitelist is None or name in whitelist) and (blacklist is None or name not in blacklist)

        if (
            global_handler_type is GlobalExtraHandlerType.BEFORE_ALL
            or global_handler_type is GlobalExtraHandlerType.AFTER_ALL
        ):
            whitelist = ["pipeline"]
            global_handler_type = (
                GlobalExtraHandlerType.BEFORE
                if global_handler_type is GlobalExtraHandlerType.BEFORE_ALL
                else GlobalExtraHandlerType.AFTER
            )

        self._services_pipeline.add_extra_handler(global_handler_type, extra_handler, condition)

    @property
    def info_dict(self) -> dict:
        """
        Property for retrieving info dictionary about this pipeline.
        Returns info dict, containing most important component public fields as well as its type.
        All complex or unserializable fields here are replaced with 'Instance of [type]'.
        """
        return {
            "type": type(self).__name__,
            "messenger_interface": f"Instance of {type(self.messenger_interface).__name__}",
            "context_storage": f"Instance of {type(self.context_storage).__name__}",
            "services": [self._services_pipeline.info_dict],
        }

    def pretty_format(self, show_extra_handlers: bool = False, indent: int = 4) -> str:
        """
        Method for receiving pretty-formatted string description of the pipeline.
        Resulting string structure is somewhat similar to YAML string.
        Should be used in debugging/logging purposes and should not be parsed.

        :param show_wrappers: Whether to include Wrappers or not (could be many and/or generated).
        :param indent: Offset from new line to add before component children.
        """
        return pretty_format_component_info_dict(self.info_dict, show_extra_handlers, indent=indent)

    @classmethod
    def from_script(
        cls,
        script: Union[Script, Dict],
        start_label: NodeLabel2Type,
        fallback_label: Optional[NodeLabel2Type] = None,
        label_priority: float = 1.0,
        validation_stage: Optional[bool] = None,
        condition_handler: Optional[Callable] = None,
        verbose: bool = True,
        handlers: Optional[Dict[ActorStage, List[Callable]]] = None,
        context_storage: Optional[Union[DBContextStorage, Dict]] = None,
        messenger_interface: Optional[MessengerInterface] = None,
        pre_services: Optional[List[Union[ServiceBuilder, ServiceGroupBuilder]]] = None,
        post_services: Optional[List[Union[ServiceBuilder, ServiceGroupBuilder]]] = None,
    ) -> "Pipeline":
        """
        Pipeline script-based constructor.
        It creates :py:class:`~.Actor` object and wraps it with pipeline.
        NB! It is generally not designed for projects with complex structure.
        :py:class:`~.Service` and :py:class:`~.ServiceGroup` customization
        becomes not as obvious as it could be with it.
        Should be preferred for simple workflows with Actor auto-execution.

        :param script: (required) A :py:class:`~.Script` instance (object or dict).
        :param start_label: (required) Actor start label.
        :param fallback_label: Actor fallback label.
        :param label_priority: Default priority value for all actor :py:const:`labels <dff.script.NodeLabel3Type>`
            where there is no priority. Defaults to `1.0`.
        :param validation_stage: This flag sets whether the validation stage is executed after actor creation.
            It is executed by default. Defaults to `None`.
        :param condition_handler: Handler that processes a call of actor condition functions. Defaults to `None`.
        :param verbose: If it is `True`, logging is used in actor. Defaults to `True`.
        :param handlers: This variable is responsible for the usage of external handlers on
            the certain stages of work of :py:class:`~dff.script.Actor`.

            - key: :py:class:`~dff.script.ActorStage` - Stage in which the handler is called.
            - value: List[Callable] - The list of called handlers for each stage. Defaults to an empty `dict`.

        :param context_storage: An :py:class:`~.DBContextStorage` instance for this pipeline
            or a dict to store dialog :py:class:`~.Context`.
        :param messenger_interface: An instance for this pipeline.
        :param pre_services: List of :py:data:`~.ServiceBuilder` or
            :py:data:`~.ServiceGroupBuilder` that will be executed before Actor.
        :type pre_services: Optional[List[Union[ServiceBuilder, ServiceGroupBuilder]]]
        :param post_services: List of :py:data:`~.ServiceBuilder` or
            :py:data:`~.ServiceGroupBuilder` that will be executed after Actor.
            It constructs root service group by merging `pre_services` + actor + `post_services`.
        :type post_services: Optional[List[Union[ServiceBuilder, ServiceGroupBuilder]]]
        """
        pre_services = [] if pre_services is None else pre_services
        post_services = [] if post_services is None else post_services
        return cls(
            script=script,
            start_label=start_label,
            fallback_label=fallback_label,
            label_priority=label_priority,
            validation_stage=validation_stage,
            condition_handler=condition_handler,
            verbose=verbose,
            handlers=handlers,
            messenger_interface=messenger_interface,
            context_storage=context_storage,
            components=[*pre_services, ACTOR, *post_services],
        )

    def set_actor(
        self,
        script: Union[Script, Dict],
        start_label: NodeLabel2Type,
        fallback_label: Optional[NodeLabel2Type] = None,
        label_priority: float = 1.0,
        validation_stage: Optional[bool] = None,
        condition_handler: Optional[Callable] = None,
        verbose: bool = True,
        handlers: Optional[Dict[ActorStage, List[Callable]]] = None,
    ):
        """
        Set actor for the current pipeline and conducts necessary checks.
        Reset actor to previous if any errors are found.

        :param script: (required) A :py:class:`~.Script` instance (object or dict).
        :param start_label: (required) Actor start label.
            The start node of :py:class:`~dff.script.Script`. The execution begins with it.
        :param fallback_label: Actor fallback label. The label of :py:class:`~dff.script.Script`.
            Dialog comes into that label if all other transitions failed,
            or there was an error while executing the scenario.
        :param label_priority: Default priority value for all actor :py:const:`labels <dff.script.NodeLabel3Type>`
            where there is no priority. Defaults to `1.0`.
        :param validation_stage: This flag sets whether the validation stage is executed in actor.
            It is executed by default. Defaults to `None`.
        :param condition_handler: Handler that processes a call of actor condition functions. Defaults to `None`.
        :param verbose: If it is `True`, logging is used in actor. Defaults to `True`.
        :param handlers: This variable is responsible for the usage of external handlers on
            the certain stages of work of :py:class:`~dff.script.Actor`.

            - key :py:class:`~dff.script.ActorStage` - Stage in which the handler is called.
            - value List[Callable] - The list of called handlers for each stage. Defaults to an empty `dict`.
        """
        old_actor = self.actor
        self.actor = Actor(script, start_label, fallback_label, label_priority, condition_handler, handlers)
        errors = self.actor.validate_script(self, verbose) if validation_stage is not False else []
        if errors:
            self.actor = old_actor
            raise ValueError(
                f"Found {len(errors)} errors: " + " ".join([f"{i}) {er}" for i, er in enumerate(errors, 1)])
            )

    @classmethod
    def from_dict(cls, dictionary: PipelineBuilder) -> "Pipeline":
        """
        Pipeline dictionary-based constructor.
        Dictionary should have the fields defined in Pipeline main constructor,
        it will be split and passed to it as `**kwargs`.
        """
        return cls(**dictionary)

    async def _run_pipeline(self, request: Message, ctx_id: Optional[Hashable] = None) -> Context:
        """
        Method that runs pipeline once for user request.

        :param request: (required) Any user request.
        :param ctx_id: Current dialog id; if `None`, new dialog will be created.
        :return: Dialog `Context`.
        """
        if ctx_id is None:
            ctx = Context()
        elif isinstance(self.context_storage, DBContextStorage):
            ctx = await self.context_storage.get_async(ctx_id, Context(id=ctx_id))
        else:
            ctx = self.context_storage.get(ctx_id, Context(id=ctx_id))

        ctx.framework_states[PIPELINE_STATE_KEY] = {}
        ctx.add_request(request)
        ctx = await self._services_pipeline(ctx, self)
        del ctx.framework_states[PIPELINE_STATE_KEY]

        if isinstance(self.context_storage, DBContextStorage):
            await self.context_storage.set_item_async(ctx_id, ctx)
        else:
            self.context_storage[ctx_id] = ctx
        if self._clean_turn_cache:
            cache_clear()

        return ctx

    def run(self):
        """
        Method that starts a pipeline and connects to `messenger_interface`.
        It passes `_run_pipeline` to `messenger_interface` as a callbacks,
        so every time user request is received, `_run_pipeline` will be called.
        This method can be both blocking and non-blocking. It depends on current `messenger_interface` nature.
        Message interfaces that run in a loop block current thread.
        """
        asyncio.run(self.messenger_interface.connect(self._run_pipeline))

    def __call__(self, request: Message, ctx_id: Hashable) -> Context:
        """
        Method that executes pipeline once.
        Basically, it is a shortcut for `_run_pipeline`.
        NB! When pipeline is executed this way, `messenger_interface` won't be initiated nor connected.

        :param request: Any user request.
        :param ctx_id: Current dialog id.
        :return: Dialog `Context`.
        """
        return asyncio.run(self._run_pipeline(request, ctx_id))

    @property
    def script(self) -> Script:
        return self.actor.script
