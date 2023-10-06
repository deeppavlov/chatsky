Context guide
--------------

Introduction
~~~~~~~~~~~~

The ``Context`` class is a backbone component of the DFF API. 
Like the name suggests, this data structure is used to store information
about the current state, or context, of a particular conversation.
Each individual user has their own ``Context`` instance and can be identified by it.

``Context`` is used to keep track of the user's requests, bot's replies,
user-related and request-related annotations, and any other information
that is relevant to the conversation with the user.

.. note::

    Since most callback functions used in DFF script and DFF pipeline (see the `basic guide <./basic_conceptions>`_)
    need to either read or update the current dialog state,
    the framework-level convention is that all functions of this kind
    use ``Context`` as their first parameter. This dependency is being
    injected by the pipeline during its run. 
    Thus, understanding the ``Context`` class is essential for developing custom conversation logic
    which is mostly made up by the said functions.

As a callback parameter, ``Context`` provides a convenient interface for working with data,
allowing developers to easily add, retrieve,
and manipulate data as the conversation progresses.

Let's consider some of the builtin callback instances to see how the context can be leveraged:

.. code-block:: python
    :linenos:

      pattern = re.compile("[a-zA-Z]+")

      def regexp_condition_handler(ctx: Context, pipeline: Pipeline, *args, **kwargs) -> bool:
          # retrieve the current request
          request = ctx.last_request
          if request.text is None:
              return False
          return bool(pattern.search(request.text))

The code above is a condition function (see the `basic guide <./basic_conceptions>`_)
that belongs to the ``TRANSITIONS`` section of the script and returns `True` or `False`
depending on whether the current user request matches the given pattern.
As can be seen from the code block, the current
request (``last_request``) can be easily retrieved as one of the attributes of the ``Context`` object.
Likewise, the ``last_response`` (bot's current reply) or the ``last_label``
(the name of the currently visited node) attributes can be used in the same manner.

Another use case is leveraging the ``misc`` field (see below for a detailed description):
pipeline functions or ``PROCESSING`` callbacks can write arbitrary values to the misc field,
making those available for other context-dependent functions.

.. code-block:: python
    :linenos:

    def save_previous_node_response_to_ctx_processing(
        ctx: Context, _: Pipeline, *args, **kwargs
    ) -> Context:
        processed_node = ctx.current_node
        ctx.misc["previous_node_response"] = processed_node.response
        return ctx

.. note::

  See more in the `pre transitions processing tutorial <../tutorials/tutorials.script.core.9_pre_transitions_processing.py>`_.

Attributes
~~~~~~~~~~~

* **id**: This attribute represents the unique context identifier. By default, it is randomly generated using uuid4.
  In most cases, this attribute will be used to identify a user

* **labels**: The labels attribute stores the history of all passed labels within the conversation.
  It maps turn IDs to labels. The collection is ordered, so getting the last item of the mapping
  always shows the last visited node.

* **requests**: The requests attribute maintains the history of all received requests by the agent.
  It also maps turn IDs to requests. Like labels, it stores the requests in-order.

* **responses**: This attribute keeps a record of all agent responses, mapping turn IDs to responses
  stores the responses in-order.

* **misc**: The misc attribute is a dictionary for storing custom data. This field is not used by any of the
  built-in DFF classes or functions, so the values that you write there are guaranteed to persist
  throughout the lifetime of the ``Context`` object.

* **validation**: A flag that signals whether validation of the script is required during pipeline initialization.
  It's important to validate custom scripts to ensure that no synthax errors have been made.

* **framework_states**: This attribute is used for storing addon or pipeline states.
  Each turn, the DFF pipeline records the intermediary states of its components into this field,
  and clears it at the end of the turn. For this reason, developers are discouraged from storing
  their own data in this field.

Methods
~~~~~~~

The methods of the ``Context`` class can be divided into two categories:

* Public methods that get called manually in custom callbacks and in functions that depend on the context.
* Methods that are not designed for manual calls and get called automatically during pipeline runs,
  i.e. quasi-private methods. You may still need them when developing extensions or heavily modifying DFF.

**Public methods**

* **last_request**: Returns the last label of the context, or `None` if the ``requests`` field is empty.

* **last_response**: Returns the last response of the context, or `None` if the ``responses`` field is empty.

* **last_label**: Returns the last label of the context, or `None` if the ``labels`` field is empty.

* **clear**: Clears all items from context fields, optionally keeping the data from `hold_last_n_indices` turns.
  You can specify which fields to clear using the `field_names` parameter. This method is designed for cases
  when contexts are shared over high latency networks.

* **overwrite_current_node_in_processing**: This method allows you to overwrite the current node with a processed node,
  but it can only be used within processing functions. This may be required when you need to temporarily substitute the current node.

.. note::

  see the `preprocessing tutorial <../tutorials/tutorials.script.core.7_pre_response_processing.py>`_.

**Private methods**

* **set_last_response, set_last_request**: These methods allow you to set the last response or request for the current context.
  This functionality can prove useful if you want to create a middleware component that overrides the pipeline functionality.

* **add_request**: Adds a request to the context for the next turn, where `request` is the request message to be added.
  It updates the `requests` dictionary. This method is called by the `Pipeline` component
  before any of the `pipeline services <../tutorials/tutorials.pipeline.3_pipeline_dict_with_services_basic.py>`_ are executed,
  including `Actor <../apiref/dff.pipeline.pipeline.actor.html>`_.

* **add_response**: Adds a response to the context for the next turn, where `response` is the response message to be added.
  It updates the `responses` dictionary. This function is run by the `Actor <../apiref/dff.pipeline.pipeline.actor.html>`_ pipeline component at the end of the turn, after it has run
  the `PRE_RESPONSE_PROCESSING <../tutorials/tutorials.script.core.7_pre_response_processing.py>`_ functions.

* **add_label**: Adds a label to the context for the next turn, where `label` is the label to be added.
  It updates the `labels` field. This method is called by the `Actor <../apiref/dff.pipeline.pipeline.actor.html>`_ component when transition conditions
  have been resolved, and when `PRE_TRANSITIONS_PROCESSING <../tutorials/tutorials.script.core.9_pre_transitions_processing.py>`_ callbacks have been run.

* **current_node**: Returns the current node of the context. This is particularly useful for tracking the node during the conversation flow.
  This method only returns a node inside ``PROCESSING`` callbacks yielding ``None`` in other contexts.

Serialization
~~~~~~~~~~~~~

The fact that the ``Context`` class is a Pydantic model makes it easily convertible to other data formats,
such as JSON. For instance, as a developer, you don't need to implement instructions on how datetime fields
need to be marshalled, since this functionality is provided by Pydantic out of the box.
As a result, working with web interfaces and databases that require the transmitted data to be serialized
becomes as easy as calling the `model_dump_json` method:

.. code-block:: python

    context = Context()
    serialized_context = context.model_dump_json()

Knowing that, you can easily extend DFF to work with storages like Memcache or web APIs of your liking.