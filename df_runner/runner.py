import uuid
from typing import ForwardRef
from typing import Any, Optional, Union, Callable
from abc import ABC, abstractmethod


from df_engine.core import Context, Actor, Script
from df_engine.core.types import NodeLabel2Type
from df_db_connector import DBAbstractConnector


Runner = ForwardRef("Runner")


class AbsRequestProvider(ABC):
    @abstractmethod
    def run(self, runner: Runner) -> bool:
        raise NotImplementedError


class CLIRequestProvider(AbsRequestProvider):
    def __init__(
        self,
        intro: Optional[str] = None,
        prompt_request: str = "request: ",
        prompt_response: str = "response: ",
    ):
        self.intro: Optional[str] = intro
        self.prompt_request: str = prompt_request
        self.prompt_response: str = prompt_response

    def run(self, runner: Runner) -> bool:
        ctx_id = uuid.uuid4()
        if self.intro is not None:
            print(self.intro)
        while True:
            request = input(self.prompt_request)
            ctx: Context = runner.request_handler(ctx_id, request)
            print(f"{self.prompt_response}{ctx.last_response}")


class Runner:
    def __init__(
        self,
        actor: Actor,
        db: DBAbstractConnector = dict(),
        request_provider: AbsRequestProvider = CLIRequestProvider(),
        pre_annotators: list = [],
        post_annotators: list = [],
        *args,
        **kwargs,
    ):
        self._db: DBAbstractConnector = db
        self._actor: Actor = actor
        self._request_provider: AbsRequestProvider = request_provider
        self._pre_annotators: list = pre_annotators
        self._post_annotators: list = post_annotators

    def start(self) -> None:
        while self._request_provider.run(self):
            pass

    def request_handler(
        self,
        ctx_id: Any,
        request: Any,
        init_ctx: Optional[Union[Context, Callable]] = None,
    ) -> Context:
        # db
        ctx: Context = self._db.get(ctx_id)
        if ctx is None:
            if init_ctx is None:
                ctx: Context = Context()
            else:
                ctx: Context = init_ctx() if callable(init_ctx) else init_ctx

        # pre_annotators
        for annotator in self._pre_annotators:
            ctx = annotator(ctx, self._actor)

        ctx.add_request(request)
        ctx = self._actor(ctx)

        # post_annotators
        for annotator in self._post_annotators:
            ctx = annotator(ctx, self._actor)

        self._db[ctx_id] = ctx

        return ctx


class ScriptRunner(Runner):
    def __init__(
        self,
        script: Union[Script, dict],
        start_label: NodeLabel2Type,
        fallback_label: Optional[NodeLabel2Type] = None,
        db: DBAbstractConnector = dict(),
        request_provider: AbsRequestProvider = CLIRequestProvider(),
        pre_annotators: list = [],
        post_annotators: list = [],
        *args,
        **kwargs,
    ):
        super(ScriptRunner, self).__init__(
            Actor(script, start_label, fallback_label),
            db,
            request_provider,
            pre_annotators,
            post_annotators,
            *args,
            **kwargs,
        )
