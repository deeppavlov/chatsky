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

Service handlers
~~~~~~~~~~~~~~~~

Service conditions
~~~~~~~~~~~~~~~~~~

Statistics extractors
~~~~~~~~~~~~~~~~~~~~~
