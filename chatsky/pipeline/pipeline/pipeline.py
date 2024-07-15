"""
Pipeline
--------
The Pipeline module contains the :py:class:`.Pipeline` class,
which is a fundamental element of Chatsky. The Pipeline class is responsible
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
from typing import Union, List, Dict, Optional, Hashable, Callable, Any
from pydantic import BaseModel, Field, model_validator, computed_field, field_validator

from chatsky.context_storages import DBContextStorage
from chatsky.script import Script, Context, ActorStage
from chatsky.script import NodeLabel2Type, Message
from chatsky.utils.turn_caching import cache_clear

from chatsky.messengers.console import CLIMessengerInterface
from chatsky.messengers.common import MessengerInterface
from chatsky.slots.slots import GroupSlot
from chatsky.pipeline.service.service import Service
from chatsky.pipeline.service.group import ServiceGroup
from chatsky.pipeline.service.extra import BeforeHandler, AfterHandler
from ..types import (
    ServiceFunction,
    GlobalExtraHandlerType,
    ExtraHandlerFunction,
    # Everything breaks without this import, even though it's unused.
    # Should it go into TYPE_CHECKING? Or what should be done?
    StartConditionCheckerFunction,
)
from .utils import finalize_service_group
from chatsky.pipeline.pipeline.actor import Actor, default_condition_handler

"""
if TYPE_CHECKING:
    from .. import Service
    from ..service.group import ServiceGroup
"""
logger = logging.getLogger(__name__)

ACTOR = "ACTOR"


# Using "arbitrary_types_allowed" from pydantic for debug purposes, probably should remove later.
# Must also add back in 'extra="forbid"', removed for testing.
class Pipeline(BaseModel,  arbitrary_types_allowed=True):
    """
    Class that automates service execution and creates service pipeline.
    It accepts constructor parameters:

    :param components: (required) A :py:data:`~.ServiceGroup` object,
        that will be transformed to root service group. It should include :py:class:`~.Actor`,
        but only once (raises exception otherwise). It will always be named pipeline.
    :param script: (required) A :py:class:`~.Script` instance (object or dict).
    :param start_label: (required) Actor start label.
    :param fallback_label: Actor fallback label.
    :param label_priority: Default priority value for all actor :py:const:`labels <dff.script.ConstLabel>`
        where there is no priority. Defaults to `1.0`.
    :param condition_handler: Handler that processes a call of actor condition functions. Defaults to `None`.
    :param handlers: This variable is responsible for the usage of external handlers on
        the certain stages of work of :py:class:`~chatsky.script.Actor`.

        - key: :py:class:`~chatsky.script.ActorStage` - Stage in which the handler is called.
        - value: List[Callable] - The list of called handlers for each stage. Defaults to an empty `dict`.

    :param messenger_interface: An `AbsMessagingInterface` instance for this pipeline.
    :param context_storage: An :py:class:`~.DBContextStorage` instance for this pipeline or
        a dict to store dialog :py:class:`~.Context`.
    :param before_handler: List of `_ComponentExtraHandler` to add to the group.
    :type before_handler: Optional[:py:data:`~._ComponentExtraHandler`]
    :param after_handler: List of `_ComponentExtraHandler` to add to the group.
    :type after_handler: Optional[:py:data:`~._ComponentExtraHandler`]
    :param timeout: Timeout to add to pipeline root service group.
    :param optimization_warnings: Asynchronous pipeline optimization check request flag;
        warnings will be sent to logs. Additionally, it has some calculated fields:

        - `_services_pipeline` is a pipeline root :py:class:`~.ServiceGroup` object,
        - `actor` is a pipeline actor, found among services.
    :param parallelize_processing: This flag determines whether or not the functions
        defined in the ``PRE_RESPONSE_PROCESSING`` and ``PRE_TRANSITIONS_PROCESSING`` sections
        of the script should be parallelized over respective groups.

    """

    # I wonder what happens/should happen here if only one callable is passed.
    pre_services: Optional[List[Union[Service, ServiceGroup]]] = []
    post_services: Optional[List[Union[Service, ServiceGroup]]] = []
    script: Union[Script, Dict]
    start_label: NodeLabel2Type
    fallback_label: Optional[NodeLabel2Type] = None
    label_priority: float = 1.0
    condition_handler: Optional[Callable] = None
    handlers: Optional[Dict[ActorStage, List[Callable]]] = None
    messenger_interface: MessengerInterface = Field(default_factory=CLIMessengerInterface)
    context_storage: Optional[Union[DBContextStorage, Dict]] = None
    before_handler: Optional[List[ExtraHandlerFunction]] = []
    after_handler: Optional[List[ExtraHandlerFunction]] = []
    timeout: Optional[float] = None
    optimization_warnings: bool = False
    parallelize_processing: bool = False
    # TO-DO: Remove/change parameters below (if possible)
    _services_pipeline: Optional[ServiceGroup]
    _clean_turn_cache: Optional[bool]

    @computed_field(alias="_services_pipeline", repr=False)
    def _services_pipeline(self) -> ServiceGroup:
        components = [*self.pre_services, self.actor, *self.post_services]
        services_pipeline = ServiceGroup(
            components=components,
            before_handler=BeforeHandler(self.before_handler),
            after_handler=AfterHandler(self.after_handler),
            timeout=self.timeout,
        )
        services_pipeline.name = "pipeline"
        services_pipeline.path = ".pipeline"
        return services_pipeline

    @computed_field(repr=False)
    def actor(self) -> Actor:
        return Actor(
            script=self.script,
            start_label=self.start_label,
            fallback_label=self.fallback_label,
            label_priority=self.label_priority,
            condition_handler=self.condition_handler,
            handlers=self.handlers,
        )

    @field_validator("before_handler")
    @classmethod
    def single_before_handler_init(cls, handler: Any):
        if isinstance(handler, ExtraHandlerFunction):
            return [handler]
        return handler

    @field_validator("after_handler")
    @classmethod
    def single_after_handler_init(cls, handler: Any):
        if isinstance(handler, ExtraHandlerFunction):
            return [handler]
        return handler

    # This looks kind of terrible. I could remove this and ask the user to do things the right way,
    # but this just seems more convenient for the user. Like, "put just one callable in pre-services"? Done.
    # TODO: Change this to a large model_validator(mode="before") for less code bloat
    @field_validator("pre_services")
    @classmethod
    def single_pre_service_init(cls, services: Any):
        if not isinstance(services, List):
            return [services]
        return services

    @field_validator("post_services")
    @classmethod
    def single_post_service_init(cls, services: Any):
        if not isinstance(services, List):
            return [services]
        return services

    @model_validator(mode="after")
    def pipeline_init(self):
        """# I wonder if I could make actor itself a @computed_field, but I'm not sure that would work.
        # What if the cache gets cleaned at some point? Then a new Actor would be created.
        # Same goes for @cached_property. Would @property work?
        self.actor = self._set_actor"""

        # finalize_service_group() needs to have the search for Actor removed.
        # Though this should work too.
        finalize_service_group(self._services_pipeline, path=self._services_pipeline.path)
        # This could be removed.
        if self.actor is None:
            raise Exception("Actor wasn't initialized correctly!")

        if self.optimization_warnings:
            self._services_pipeline.log_optimization_warnings()

        # NB! The following API is highly experimental and may be removed at ANY time WITHOUT FURTHER NOTICE!!
        self._clean_turn_cache = True
        if self._clean_turn_cache:
            self.actor._clean_turn_cache = False
        return self

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

    @classmethod
    def from_script(
        cls,
        script: Union[Script, Dict],
        start_label: NodeLabel2Type,
        fallback_label: Optional[NodeLabel2Type] = None,
        label_priority: float = 1.0,
        condition_handler: Optional[Callable] = default_condition_handler,
        slots: Optional[Union[GroupSlot, Dict]] = None,
        parallelize_processing: bool = False,
        handlers: Optional[Dict[ActorStage, List[Callable]]] = None,
        context_storage: Optional[Union[DBContextStorage, Dict]] = None,
        messenger_interface: Optional[MessengerInterface] = CLIMessengerInterface(),
        pre_services: Optional[List[Union[ServiceFunction, ServiceGroup]]] = None,
        post_services: Optional[List[Union[ServiceFunction, ServiceGroup]]] = None,
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
        :param label_priority: Default priority value for all actor :py:const:`labels <chatsky.script.ConstLabel>`
            where there is no priority. Defaults to `1.0`.
        :param condition_handler: Handler that processes a call of actor condition functions. Defaults to `None`.
        :param slots: Slots configuration.
        :param parallelize_processing: This flag determines whether or not the functions
            defined in the ``PRE_RESPONSE_PROCESSING`` and ``PRE_TRANSITIONS_PROCESSING`` sections
            of the script should be parallelized over respective groups.
        :param handlers: This variable is responsible for the usage of external handlers on
            the certain stages of work of :py:class:`~chatsky.script.Actor`.

            - key: :py:class:`~chatsky.script.ActorStage` - Stage in which the handler is called.
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
            condition_handler=condition_handler,
            slots=slots,
            parallelize_processing=parallelize_processing,
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
        condition_handler: Optional[Callable] = None,
        handlers: Optional[Dict[ActorStage, List[Callable]]] = None,
    ):
        """
        Set actor for the current pipeline and conducts necessary checks.
        Reset actor to previous if any errors are found.

        :param script: (required) A :py:class:`~.Script` instance (object or dict).
        :param start_label: (required) Actor start label.
            The start node of :py:class:`~chatsky.script.Script`. The execution begins with it.
        :param fallback_label: Actor fallback label. The label of :py:class:`~chatsky.script.Script`.
            Dialog comes into that label if all other transitions failed,
            or there was an error while executing the scenario.
        :param label_priority: Default priority value for all actor :py:const:`labels <chatsky.script.ConstLabel>`
            where there is no priority. Defaults to `1.0`.
        :param condition_handler: Handler that processes a call of actor condition functions. Defaults to `None`.
        :param handlers: This variable is responsible for the usage of external handlers on
            the certain stages of work of :py:class:`~chatsky.script.Actor`.

            - key :py:class:`~chatsky.script.ActorStage` - Stage in which the handler is called.
            - value List[Callable] - The list of called handlers for each stage. Defaults to an empty `dict`.
        """
        self.actor = Actor(
            script=script,
            start_label=start_label,
            fallback_label=fallback_label,
            label_priority=label_priority,
            condition_handler=condition_handler,
            handlers=handlers,
        )

    @classmethod
    def from_dict(cls, dictionary: dict) -> "Pipeline":
        """
        Pipeline dictionary-based constructor.
        Dictionary should have the fields defined in Pipeline main constructor,
        it will be split and passed to it as `**kwargs`.
        """
        return cls(**dictionary)

    async def _run_pipeline(
        self, request: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
    ) -> Context:
        """
        Method that should be invoked on user input.
        This method has the same signature as :py:class:`~chatsky.pipeline.types.PipelineRunnerFunction`.
        """
        if ctx_id is None:
            ctx = Context()
        elif isinstance(self.context_storage, DBContextStorage):
            ctx = await self.context_storage.get_async(ctx_id, Context(id=ctx_id))
        else:
            ctx = self.context_storage.get(ctx_id, Context(id=ctx_id))

        if update_ctx_misc is not None:
            ctx.misc.update(update_ctx_misc)

        if self.slots is not None:
            ctx.framework_data.slot_manager.set_root_slot(self.slots)

        ctx.add_request(request)
        result = await self._services_pipeline(ctx, self)

        if asyncio.iscoroutine(result):
            await result

        ctx.framework_data.service_states.clear()

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

    def __call__(
        self, request: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
    ) -> Context:
        """
        Method that executes pipeline once.
        Basically, it is a shortcut for `_run_pipeline`.
        NB! When pipeline is executed this way, `messenger_interface` won't be initiated nor connected.

        This method has the same signature as :py:class:`~chatsky.pipeline.types.PipelineRunnerFunction`.
        """
        return asyncio.run(self._run_pipeline(request, ctx_id, update_ctx_misc))

    @property
    def script(self) -> Script:
        return self.actor.script