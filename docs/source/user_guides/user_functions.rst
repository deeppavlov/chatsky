User functions guide
--------------------

Overview
~~~~~~~~

Dialog flow franework allows user to define custom functions for implementaing custom behavior
in several aspects.
This tutorial summarizes the custom functions use cases, specifies their arguments and return
types, warns about several common exception handling.

``Actor`` handlers
~~~~~~~~~~~~~~~~~~

`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_ constructor accepts ``handlers``
parameter, that is either ``None`` or dictionary attributing lists of functions to different
`ActorStage <../api/dff.script.core.types#ActorStage>`_ values.

These functions are run at specific point in `Actor <../api/dff.pipeline.pipeline.actor#Actor>`_
lifecycle.
Each of these functions has the following signature:

.. code-block:: python

    def handler(ctx: Context, pipeline: Pipeline) -> Any:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and the return value can be anything (it is not used).

Pre-transition processors
~~~~~~~~~~~~~~~~~~~~~~~~~

Each script `Node <../api/dff.script.core.script#Node>`_ has a property called ``pre_transitions_processing``.
That is a dictionary, associating functions to their names (that can be any hashable object).

These functions are run before transition from the previous node to the current node.
Each of these functions has the following signature:

.. code-block:: python

    def handler(ctx: Context, pipeline: Pipeline) -> Context:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and the return value is the modified Context value.

Pre-response processors
~~~~~~~~~~~~~~~~~~~~~~~

Each script `Node <../api/dff.script.core.script#Node>`_ has a property called ``pre_response_processing``.
That is a dictionary, associating functions to their names (that can be any hashable object).

These functions are run before acquiring the response, after the current node is processed.
Each of these functions has the following signature:

.. code-block:: python

    def handler(ctx: Context, pipeline: Pipeline) -> Context:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and the return value is the modified Context value.

Script conditions and condition handlers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each transition between different nodes in `Script <../api/dff.script.core.script#Script>`_
has a condition function.
They are provided in script dictionary (TODO: parser?) in form of Python functions.

These functions are executed on pipeline startup if ``validation_stage`` parameter of
`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_ is ``True`` and before transition
from the corresponding node in script in runtime.
Each of these functions has the following signature:

.. code-block:: python

    def condition(ctx: Context, pipeline: Pipeline) -> bool:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and the return value is ``True`` if transition should be made and ``False`` otherwise.

There is a set of `standard condition functions <../api/dff.script.conditions.std_conditions>`_ defined.

`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_ constructor also accepts
condition handler - that is a special function that executes conditions.

This function is invoked every time condition should be checked, it launches and checks condition.
This function has the following signature:

.. code-block:: python

    def condition_handler(condition: Callable[[Context, Pipeline], bool], ctx: Context, pipeline: Pipeline) -> bool:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and the return value is ``True`` if transition should be made and ``False`` otherwise.

The simplest `default condition handler <../api/dff.pipeline.pipeline.actor#default_condition_handler>`_
just invokes the condition function and returns the result.

Labels
~~~~~~

Some of the transitions between nodes in `Script <../api/dff.script.core.script#Script>`_
do not have "absolute" node targets specified.
For instance, that might be useful in case it is required to stay in the same node or transition
to the previous node.
For such cases special function node labels can be used.

These functions are executed on pipeline startup if ``validation_stage`` parameter of
`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_ is ``True`` and before transition
from the corresponding node in script in runtime.
Each of these functions has the following signature:

.. code-block:: python

    def label(ctx: Context, pipeline: Pipeline) -> Tuple[str, str, float]:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and the return value is an instance of `NodeLabel3Type <../api/dff.script.core.types#NodeLabel3Type>`,
that is a tuple of target flow name (``str``), node name (``str``) and priority (``float``).

There is a set of `standard label functions <../api/dff.script.conditions.std_labels>`_ defined.

Responses
~~~~~~~~~

For some of the nodes in `Script <../api/dff.script.core.script#Script>`_ returning constant values
might be not enough.
For these cases each return value can be represented as a Python function.

These functions are executed on pipeline startup if ``validation_stage`` parameter of
`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_ is ``True`` and in the end
of any node processing in runtime.
Each of these functions has the following signature:

.. code-block:: python

    def response(ctx: Context, pipeline: Pipeline) -> Message:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and the return value is an instance of `Message <../api/dff.script.core.message#Message>`.

Extra handlers
~~~~~~~~~~~~~~

For some (or all) services in a `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_ special
extra handler functions can be added.
These functions can handle statistics collection, input data transformation
or other pipeline functionality extension.

These functions can be either added to `pipeline dict <../api/dff.pipeline.types#PipelineBuilder>`_
or added to all services at once with `add_global_handler <../api/dff.pipeline.pipeline.pipeline#add_global_handler>`_
function.
The handlers can be executed before or after pipeline services.
Each of them has one of the following signatures:

.. code-block:: python

    async def handler(ctx: Context) -> Any:
        ...

    async def handler(ctx: Context, pipeline: Pipeline) -> Any:
        ...

    async def handler(ctx: Context, pipeline: Pipeline, runtime_info: Dict) -> Any:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_,
where ``runtime_info`` is a `runtime info dictionary <../api/dff.pipeline.types#ExtraHandlerRuntimeInfo>`_
and the return value can be anything (it is not used).

Service handlers
~~~~~~~~~~~~~~~~

`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_ services (other than `Actor <../api/dff.pipeline.pipeline.pipeline#ACTOR>`_)
should be represented as functions.
These functions can be run sequentially or combined into several asynchronous groups.
The handlers can, for instance, process data, make web requests, read and write files, etc.

The services are executed on every `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_ run,
they can happen before or after `Actor <../api/dff.pipeline.pipeline.pipeline#ACTOR>`_ execution.
Each of them has one of the following signatures:

.. code-block:: python

    async def handler(ctx: Context) -> Any:
        ...

    async def handler(ctx: Context, pipeline: Pipeline) -> Any:
        ...

    async def handler(ctx: Context, pipeline: Pipeline, runtime_info: Dict) -> Any:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_,
where ``runtime_info`` is a `runtime info dictionary <../api/dff.pipeline.types#ExtraHandlerRuntimeInfo>`_
and the return value can be anything (it is not used).

Service conditions
~~~~~~~~~~~~~~~~~~

`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_ services (other than `Actor <../api/dff.pipeline.pipeline.pipeline#ACTOR>`_)
can be executed conditionally.
For that some special conditions should be used (that are in a way similar to `Script conditions and condition handlers`_).
However, there is no such thing as ``condition handler`` function in pipeline.

These conditions are only run before services they are related to, that can be any services **except for Actor**.
Each of these functions has the following signature:

.. code-block:: python

    def condition(ctx: Context, pipeline: Pipeline) -> bool:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and the return value is ``True`` if the service should be run and ``False`` otherwise.

There is a set of `standard condition functions <../api/dff.pipeline.conditions>`_ defined.

Statistics extractors
~~~~~~~~~~~~~~~~~~~~~

`OtelInstrumentor <../api/dff.stats.instrumentor#OtelInstrumentor>`_ has some wrapper functions,
added to it on ``instrument`` call.
These functions can extract and process telemetry statistics.

The extractors are run upon ``__call__`` of the instrumentor.
They have the following signature:

.. code-block:: python

    def extractor(ctx: Context, _: ???, runtime_info: Dict) -> None:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and ``runtime_info`` is a `runtime info dictionary <../api/dff.pipeline.types#ExtraHandlerRuntimeInfo>`_.

There is a set of `standard statistics extractors <../api/dff.stats.default_extractors>`_ defined.
