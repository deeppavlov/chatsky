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

    Since most callback functions used in DFF script and DFF pipeline (see the `basic guide <./basic_conceptions.rst>`__)
    need to either read or update the current dialog state,
    the framework-level convention is that all functions of this kind
    use ``Context`` as their first parameter. This dependency is being
    injected by the pipeline during its run. 
    Thus, understanding the ``Context`` class is essential for developing custom conversation logic
    which is mostly made up by the said functions.

As a callback parameter, ``Context`` provides a convenient interface for working with data,
allowing developers to easily add, retrieve,
and manipulate data as the conversation progresses.

Let's consider some of the built-in callback instances to see how the context can be leveraged:

.. code-block:: python
    :linenos:

      pattern = re.compile("[a-zA-Z]+")

      def regexp_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
          # retrieve the current request
          request = ctx.last_request
          if request.text is None:
              return False
          return bool(pattern.search(request.text))

The code above is a condition function (see the `basic guide <./basic_conceptions.rst>`__)
that belongs to the ``TRANSITIONS`` section of the script and returns `True` or `False`
depending on whether the current user request matches the given pattern.
As can be seen from the code block, the current
request (``last_request``) can be easily retrieved as one of the attributes of the ``Context`` object.
Likewise, the ``last_response`` (bot's current reply) or the ``last_label``
(the name of the currently visited node) attributes can be used in the same manner.

Another common use case is leveraging the ``misc`` field (see below for a detailed description):
pipeline functions or ``PROCESSING`` callbacks can write arbitrary values to the misc field,
making those available for other context-dependent functions.

.. code-block:: python
    :linenos:

    import urllib.request
    import urllib.error

    def ping_example_com(
        ctx: Context, *_, **__
    ):
        try:
            with urllib.request.urlopen("https://example.com/") as webpage:
                web_content = webpage.read().decode(
                    webpage.headers.get_content_charset()
                )
                result = "Example Domain" in web_content
        except urllib.error.URLError:
            result = False
        ctx.misc["can_ping_example_com"] = result

..
    todo: link to the user defined functions tutorial

    .. note::
        For more information about user-defined functions see the `user functions guide <./user_functions.rst>`__.

API
~~~

This sections describes the API of the ``Context`` class.

For more information, such as method signatures, see
`API reference <../apiref/dff.script.core.context.html#dff.script.core.context.Context>`__.

Attributes
==========

* **id**: This attribute represents the unique context identifier. By default, it is randomly generated using uuid4.
  In most cases, this attribute will be used to identify a user.

* **labels**: The labels attribute stores the history of all passed labels within the conversation.
  It maps turn IDs to labels. The collection is ordered, so getting the last item of the mapping
  always shows the last visited node.

  Note that `labels` only stores the nodes that were transitioned to
  so `start_label` will not be in this attribute.

* **requests**: The requests attribute maintains the history of all received requests by the agent.
  It also maps turn IDs to requests. Like labels, it stores the requests in-order.

* **responses**: This attribute keeps a record of all agent responses, mapping turn IDs to responses.
  Stores the responses in-order.

* **misc**: The misc attribute is a dictionary for storing custom data. This field is not used by any of the
  built-in DFF classes or functions, so the values that you write there are guaranteed to persist
  throughout the lifetime of the ``Context`` object.

* **framework_states**: This attribute is used for storing addon or pipeline states.
  Each turn, the DFF pipeline records the intermediary states of its components into this field,
  and clears it at the end of the turn. For this reason, developers are discouraged from storing
  their own data in this field.

Methods
=======

The methods of the ``Context`` class can be divided into two categories:

* Public methods that get called manually in custom callbacks and in functions that depend on the context.
* Methods that are not designed for manual calls and get called automatically during pipeline runs,
  i.e. quasi-private methods. You may still need them when developing extensions or heavily modifying DFF.

Public methods
^^^^^^^^^^^^^^

* **last_request**: Return the last request of the context, or `None` if the ``requests`` field is empty.

  Note that a request is added right after the context is created/retrieved from db,
  so an empty ``requests`` field usually indicates an issue with the messenger interface.

* **last_response**: Return the last response of the context, or `None` if the ``responses`` field is empty.

  Responses are added at the end of each turn, so an empty ``response`` field is something you should definitely consider.

* **last_label**: Return the last label of the context, or `None` if the ``labels`` field is empty.
  Last label is always the name of the current node but not vice versa:

  Since ``start_label`` is not added to the ``labels`` field,
  empty ``labels`` usually indicates that the current node is the `start_node`.
  After a transition is made from the `start_node`
  the label of that transition is added to the field.

* **clear**: Clear all items from context fields, optionally keeping the data from `hold_last_n_indices` turns.
  You can specify which fields to clear using the `field_names` parameter. This method is designed for cases
  when contexts are shared over high latency networks.

.. note::

  See the `preprocessing tutorial <../tutorials/tutorials.script.core.7_pre_response_processing.py>`__.

Private methods
^^^^^^^^^^^^^^^

* **set_last_response, set_last_request**: These methods allow you to set the last response or request for the current context.
  This functionality can prove useful if you want to create a middleware component that overrides the pipeline functionality.

* **add_request**: Add a request to the context.
  It updates the `requests` dictionary. This method is called by the `Pipeline` component
  before any of the `pipeline services <../tutorials/tutorials.pipeline.3_pipeline_dict_with_services_basic.py>`__ are executed,
  including `Actor <../apiref/dff.pipeline.pipeline.actor.html>`__.

* **add_response**: Add a response to the context.
  It updates the `responses` dictionary. This function is run by the `Actor <../apiref/dff.pipeline.pipeline.actor.html>`__ pipeline component at the end of the turn, after it has run
  the `PRE_RESPONSE_PROCESSING <../tutorials/tutorials.script.core.7_pre_response_processing.py>`__ functions.

  To be more precise, this method is called between the ``CREATE_RESPONSE`` and ``FINISH_TURN`` stages.
  For more information about stages, see `ActorStages <../apiref/dff.script.core.types.html#dff.script.core.types.ActorStage>`__.

* **add_label**: Add a label to the context.
  It updates the `labels` field. This method is called by the `Actor <../apiref/dff.pipeline.pipeline.actor.html>`_ component when transition conditions
  have been resolved, and when `PRE_TRANSITIONS_PROCESSING <../tutorials/tutorials.script.core.9_pre_transitions_processing.py>`__ callbacks have been run.

  To be more precise, this method is called between the ``GET_NEXT_NODE`` and ``REWRITE_NEXT_NODE`` stages.
  For more information about stages, see `ActorStages <../apiref/dff.script.core.types.html#dff.script.core.types.ActorStage>`__.

* **current_node**: Return the current node of the context. This is particularly useful for tracking the node during the conversation flow.
  This method only returns a node inside ``PROCESSING`` callbacks yielding ``None`` in other contexts.

Context storages
~~~~~~~~~~~~~~~~

Since context instances contain all the information, relevant for a particular user, there needs to be a way
to persistently store that information and to make it accessible in different user sessions.
This functionality is implemented by the ``context storages`` module that provides 
the uniform ``DBContextStorage`` interface as well as child classes thereof that integrate
various database types (see the
`api reference <../apiref/dff.context_storages.database.html#dff.context_storages.database.DBContextStorage>`_).

The supported storage options are as follows:

* `JSON <https://www.json.org/json-en.html>`_
* `pickle <https://docs.python.org/3/library/pickle.html>`_
* `shelve <https://docs.python.org/3/library/shelve.html>`_
* `SQLite <https://www.sqlite.org/index.html>`_
* `PostgreSQL <https://www.postgresql.org/>`_
* `MySQL <https://www.mysql.com/>`_
* `MongoDB <https://www.mongodb.com/>`_
* `Redis <https://redis.io/>`_
* `Yandex DataBase <https://ydb.tech/>`_

``DBContextStorage`` instances can be uniformly constructed using the ``context_storage_factory`` function.
The function's only parameter is a connection string that specifies both the database type
and the connection parameters, for example, *mongodb://admin:pass@localhost:27016/admin*.
(`see the reference <../apiref/dff.context_storages.database.html#dff.context_storages.database.context_storage_factory>`_)

.. note::
    To learn how to use ``context_storage_factory`` in your pipeline, see our `Context Storage Tutorials <../tutorials/index_context_storages.html>`__.

The GitHub-based distribution of DFF includes Docker images for each of the supported database types.
Therefore, the easiest way to deploy your service together with a database is to clone the GitHub
distribution and to take advantage of the packaged
`docker compose file <https://github.com/deeppavlov/dialog_flow_framework/blob/master/compose.yml>`_.

.. code-block:: shell
  :linenos:

  git clone https://github.com/deeppavlov/dialog_flow_framework.git
  cd dialog_flow_framework
  # assuming we need to deploy mongodb
  docker compose up mongo

The images can be configured using the docker compose file or the
`environment file <https://github.com/deeppavlov/dialog_flow_framework/blob/master/.env_file>`_,
also available in the distribution. Consult these files for more options.

.. warning::

  The data transmission protocols require the data to be JSON-serializable. DFF tackles this problem
  through utilization of ``pydantic`` as described in the next section.

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