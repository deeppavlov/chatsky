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
Each of these functions have to have the following signature:

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
Each of these functions have to have the following signature:

.. code-block:: python

    def handler(ctx: Context, pipeline: Pipeline) -> Context:
        ...

where ``ctx`` is the current instance of `Context <../api/dff.script.core.context#Context>`_,
where ``pipeline`` is the current instance of `Pipeline <../api/dff.pipeline.pipeline.pipeline#Pipeline>`_
and the return value is the modified Context value.
