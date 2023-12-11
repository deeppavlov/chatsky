User functions guide
--------------------

Overview
++++++++

Dialog flow framework allows user to define custom functions for implementing custom behavior
in several aspects.
This tutorial summarizes the custom functions use cases, specifies their arguments and return
types, warns about several common exception handling cases.

``Actor`` handlers
++++++++++++++++++

Description
~~~~~~~~~~~

`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__ constructor accepts ``handlers``
parameter, that is either ``None`` or dictionary attributing lists of functions to different
`ActorStage <../api/dff.script.core.types#ActorStage>`__ values.

These functions are run at specific point in `Actor <../api/dff.pipeline.pipeline.actor#Actor>`__
lifecycle.

Use-cases
~~~~~~~~~

TODO

Signature
~~~~~~~~~

.. code-block:: python

    def handler(ctx: Context, pipeline: Pipeline) -> Any:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__
and the return value can be anything (it is not used).

Exceptions
~~~~~~~~~~

If an exception occurs during this function execution, it will be handled on pipeline level,
exception message will be printed to ``stdout`` and the actor service `state <../api/dff.pipeline.types#ComponentExecutionState>`__
will be set to ``FAILED``.
These exceptions **are not raised** during script validation.

Script functions
++++++++++++++++

Pre-transition and pre-response processors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Description
===========

Each script `Node <../api/dff.script.core.script#Node>`__ has a properties called
``pre_transitions_processing`` and ``pre_response_processing``.
That is a dictionary, associating functions to their names (that can be any hashable object).

Pre-transition proccessors are run before transition from the previous node to the current node.
Pre-response proccessors are run before acquiring the response, after the current node is processed.

Use-cases
=========

TODO

See tutorials:

#. `About pre-transition processors <../tutorials/tutorials.script.core.9_pre_transitions_processing>`__
#. `About pre-response processors <../tutorials/tutorials.script.core.7_pre_response_processing>`__

Signature
=========

.. code-block:: python

    def handler(ctx: Context, pipeline: Pipeline) -> Context:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__
and the return value is the modified Context value.

Exceptions
==========

If an exception occurs during this function execution, it will be handled internally,
only an exception message will be printed to ``stdout``.
These exceptions **are not raised** during script validation.

Script conditions and condition handlers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Description of condition
========================

Each transition between different nodes in `Script <../api/dff.script.core.script#Script>`__
has a condition function.
They are provided in script dictionary (TODO: parser?) in form of Python functions.

These functions are executed on pipeline startup if ``validation_stage`` parameter of
`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__ is ``True`` and before transition
from the corresponding node in script in runtime.

Use-cases
=========

TODO

See `tutorial about conditions <../tutorials/tutorials.script.core.2_conditions>`__.

Signature of condition
======================

.. code-block:: python

    def condition(ctx: Context, pipeline: Pipeline) -> bool:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__
and the return value is ``True`` if transition should be made and ``False`` otherwise.

Standard conditions
===================

There is a set of `standard script condition functions <../api/dff.script.conditions.std_conditions>`__ defined.

Exceptions in conditions
========================

If an exception occurs during this function execution, it will be reported during script validation stage
(if any) and also will be handled on pipeline level,
exception message will be printed to ``stdout`` and the actor service `state <../api/dff.pipeline.types#ComponentExecutionState>`__
will be set to ``FAILED``.

Description of condition handler
================================

`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__ constructor also accepts
condition handler - that is a special function that executes conditions.

This function is invoked every time condition should be checked, it launches and checks condition.

Use-cases
=========

TODO

Signature of condition handler
==============================

.. code-block:: python

    def condition_handler(condition: Callable[[Context, Pipeline], bool], ctx: Context, pipeline: Pipeline) -> bool:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__
and the return value is ``True`` if transition should be made and ``False`` otherwise.

Standard condition handler
==========================

The simplest `default condition handler <../api/dff.pipeline.pipeline.actor#default_condition_handler>`__
just invokes the condition function and returns the result.

Exceptions in condition handler
================================

If an exception occurs during this function execution, it will be reported during script validation stage
(if any), otherwise it will be handled on pipeline level,
exception message will be printed to ``stdout`` and the actor service `state <../api/dff.pipeline.types#ComponentExecutionState>`__
will be set to ``FAILED``.

Labels
~~~~~~

Description
===========

Some of the transitions between nodes in `Script <../api/dff.script.core.script#Script>`__
do not have "absolute" node targets specified.
For instance, that might be useful in case it is required to stay in the same node or transition
to the previous node.
For such cases special function node labels can be used.

These functions are executed on pipeline startup if ``validation_stage`` parameter of
`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__ is ``True`` and before transition
from the corresponding node in script in runtime.

Use-cases
=========

TODO

See `tutorial about transition functions <../tutorials/tutorials.script.core.4_transitions>`__.

Signature
=========

.. code-block:: python

    def label(ctx: Context, pipeline: Pipeline) -> Tuple[str, str, float]:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__
and the return value is an instance of `NodeLabel3Type <../api/dff.script.core.types#NodeLabel3Type>`__,
that is a tuple of target flow name (``str``), node name (``str``) and priority (``float``).

Standard
========

There is a set of `standard label functions <../api/dff.script.conditions.std_labels>`__ defined.

Exceptions
==========

If an exception occurs during this function execution, it will be reported during script validation stage
(if any), otherwise it will be handled internally, only an exception message will be printed to ``stdout``.

Responses
~~~~~~~~~

Description
===========

For some of the nodes in `Script <../api/dff.script.core.script#Script>`__ yielding constant response values
might be not enough.
For these cases each response can be represented as a Python function.

These functions are executed on pipeline startup if ``validation_stage`` parameter of
`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__ is ``True`` and in the end
of any node processing in runtime.

Use-cases
=========

TODO

See `tutorial about response functions <../tutorials/tutorials.script.core.3_responses>`__.

Signature
=========

.. code-block:: python

    def response(ctx: Context, pipeline: Pipeline) -> Message:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__
and the return value is an instance of `Message <../api/dff.script.core.message#Message>`__.

Exceptions
==========

If an exception occurs during this function execution, it will be reported during script validation stage
(if any), otherwise it will be handled on pipeline level,
exception message will be printed to ``stdout`` and the actor service `state <../api/dff.pipeline.types#ComponentExecutionState>`__
will be set to ``FAILED``.

Service functions
+++++++++++++++++

Service handlers
~~~~~~~~~~~~~~~~

Description
===========

`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__ services (other than `Actor <../api/dff.pipeline.pipeline.pipeline#ACTOR>`__)
should be represented as functions.
These functions can be run sequentially or combined into several asynchronous groups.
The handlers can, for instance, process data, make web requests, read and write files, etc.

The services are executed on every `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__ run,
they can run before or after `Actor <../api/dff.pipeline.pipeline.pipeline#ACTOR>`__ execution.

Use-cases
=========

TODO

See tutorials:

#. `About synchronous services (basic) <../tutorials/tutorials.pipeline.3_pipeline_dict_with_services_basic>`__
#. `About synchronous services (advanced) <../tutorials/tutorials.pipeline.3_pipeline_dict_with_services_full>`__
#. `About asynchronous services (basic) <../tutorials/tutorials.pipeline.5_asynchronous_groups_and_services_basic>`__
#. `About asynchronous services (advanced) <../tutorials/tutorials.pipeline.5_asynchronous_groups_and_services_full>`__

Signatures
==========

.. code-block:: python

    async def handler(ctx: Context) -> Any:
        ...

    async def handler(ctx: Context, pipeline: Pipeline) -> Any:
        ...

    async def handler(ctx: Context, pipeline: Pipeline, runtime_info: Dict) -> Any:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__,
where ``runtime_info`` is a `runtime info dictionary <../api/dff.pipeline.types#ExtraHandlerRuntimeInfo>`__
and the return value can be anything (it is not used).

Exceptions
==========

If this function exceeds timeout (that implies that ``TimeoutError`` is thrown), it will be interrupted
in parent `ServiceGroup <../api/dff.pipeline.service.group#ServiceGroup>`__ and an exception message will be printed to ``stdout``.
If any other exception occurs during this function execution, it will be handled on pipeline level,
exception message will be printed to ``stdout`` and the service `state <../api/dff.pipeline.types#ComponentExecutionState>`__
will be set to ``FAILED``.

Service conditions
~~~~~~~~~~~~~~~~~~

Description
===========

`Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__ services (other than `Actor <../api/dff.pipeline.pipeline.pipeline#ACTOR>`__)
can be executed conditionally.
For that some special conditions should be used (that are in a way similar to `Script conditions and condition handlers`_).
However, there is no such thing as ``condition handler`` function in pipeline.

These conditions are only run before services they are related to, that can be any services **except for Actor**.

Use-cases
=========

TODO

See tutorials:

#. `About service groups and conditions (basic) <../tutorials/tutorials.pipeline.4_groups_and_conditions_basic>`__
#. `About service groups and conditions (advanced) <../tutorials/tutorials.pipeline.4_groups_and_conditions_full>`__

Signature
=========

.. code-block:: python

    def condition(ctx: Context, pipeline: Pipeline) -> bool:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__
and the return value is ``True`` if the service should be run and ``False`` otherwise.

Standard
========

There is a set of `standard service condition functions <../api/dff.pipeline.conditions>`__ defined.

Exceptions
==========

If any other exception occurs during this function execution, it will be handled on pipeline level,
exception message will be printed to ``stdout`` and the service `state <../api/dff.pipeline.types#ComponentExecutionState>`__
will be set to ``FAILED``.

Extra handlers
~~~~~~~~~~~~~~

Description
===========

For any service in a `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__ special
extra handler functions can be added.
These functions can handle statistics collection, input data transformation
or other pipeline functionality extension.

These functions can be either added to `pipeline dict <../api/dff.pipeline.types#PipelineBuilder>`__
or added to all services at once with `add_global_handler <../api/dff.pipeline.pipeline.pipeline#add_global_handler>`__
function.
The handlers can be executed before or after pipeline services.

Use-cases
=========

TODO

See tutorials:

#. `About extra handlers (basic) <../tutorials/tutorials.pipeline.7_extra_handlers_basic>`__
#. `About extra handlers (advanced) <../tutorials/tutorials.pipeline.7_extra_handlers_full>`__
#. `About extra handlers and extensions <../tutorials/tutorials.pipeline.8_extra_handlers_and_extensions>`__

Signatures
==========

.. code-block:: python

    async def handler(ctx: Context) -> Any:
        ...

    async def handler(ctx: Context, pipeline: Pipeline) -> Any:
        ...

    async def handler(ctx: Context, pipeline: Pipeline, runtime_info: Dict) -> Any:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__,
where ``runtime_info`` is a `runtime info dictionary <../api/dff.pipeline.types#ExtraHandlerRuntimeInfo>`__
and the return value can be anything (it is not used).

Exceptions
==========

If this function exceeds timeout (that implies that ``TimeoutError`` is thrown), it will be interrupted
and an exception message will be printed to ``stdout``.
If any other exception occurs during this function execution, it **will not** be handled on pipeline level,
it will either be reported in parent `ServiceGroup <../api/dff.pipeline.service.group#ServiceGroup>`__ or interrupt pipeline execution.

Statistics extractors
~~~~~~~~~~~~~~~~~~~~~

Description
===========

Statistics module introduces the concept of extractor functions.
These are equivalent to pipeline's regular extra handlers (described above) except that
they have to be decorated by Opentelemetry's `OtelInstrumentor <../api/dff.stats.instrumentor#OtelInstrumentor>`_
class that proxies the output of these handlers and redirects it to Opentelemetry services.

See the `extractor function tutorial <../tutorials/tutorials.stats.1_extractor_functions.py>`__ for reference.

Use-cases
=========

TODO

See `tutorial about extractor functions <../tutorials/tutorials.stats.1_extractor_functions>`__.

Signature
=========

.. code-block:: python

    def extractor(ctx: Context, pipeline: Pipeline, runtime_info: Dict) -> None:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`__,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`__
and ``runtime_info`` is a `runtime info dictionary <../api/dff.pipeline.types#ExtraHandlerRuntimeInfo>`__.

Standard
========

There is a set of `standard statistics extractors <../api/dff.stats.default_extractors>`__ defined.

Exceptions
==========

If an exception occurs during this function execution, it is not handled and will be thrown
during `OtelInstrumentor <../api/dff.stats.instrumentor#OtelInstrumentor>`__ ``__call__``
function execution.
