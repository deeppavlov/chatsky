Context guide
--------------

Introduction
~~~~~~~~~~~~

The `Context` class is a backbone component of the DFF API. 
Like the name suggests, this data structure is used to store information
about the current state of a particular conversation,
i.e. each individual user has their own context instance and can be identified by it.

`Context` is used to keep track of the user's requests, bot's replies,
user-related and request-related annotations, and any other information
that is relevant to the conversation with the user.

.. warning::

    Since most callback functions used in DFF script and DFF pipeline (see the `basic guide <./basic_conceptions>`_)
    need to either read or update the current dialog state,
    the framework-level convention is that all functions of this kind
    use `Context` as their first parameter. This dependency is being
    injected by the pipeline during its run. Thus, understanding
    the `Context` class is essential for developing custom conversation logic
    that is mostly made up by the said functions.

`Context` provides a convenient interface for working with data,
allowing developers to easily add, retrieve,
and manipulate data as the conversation progresses.

Attributes
~~~~~~~~~~~

* `id`: This attribute represents the unique context identifier. By default, it is randomly generated using uuid4. The id can be used for tracing user behavior and collecting statistical data.

* `labels`: The labels attribute stores the history of all passed labels within the conversation. It maps turn IDs to labels.

* `requests`: The requests attribute maintains the history of all received requests by the agent. It also maps turn IDs to requests.

* `responses`: This attribute keeps a record of all agent responses, mapping turn IDs to responses.

* `misc`: The misc attribute is a dictionary for storing custom data. The scripting in DFF doesn't use this dictionary by default.

* `validation`: A flag that signals whether validation of the script is required during pipeline initialization. Some functions that may produce invalid data must consider this flag for successful validation.

* `framework_states`: This attribute is used for storing addon or pipeline states. Pipeline records all its intermediate conditions into framework_states, and after context processing is completed, it resets the framework_states and returns the context.

Key Methods
~~~~~~~~~~~~

The `Context` class provides essential methods for working with data:

* **`add_request(request: Message)`**: Adds a request to the context for the next turn, where `request` is the request message to be added. It updates the `requests` dictionary.

* **`add_response(response: Message)`**: Adds a response to the context for the next turn, where `response` is the response message to be added. It updates the `responses` dictionary.

* **`add_label(label: NodeLabel2Type)`**: Adds a label to the context for the next turn, where `label` is the label to be added. It updates the `labels` dictionary.

* **`clear(hold_last_n_indices: int, field_names: Union[Set[str], List[str]])`**: Clears all recordings from the context, except for the last `hold_last_n_indices` turns. You can specify which fields to clear using the `field_names` parameter.

* **`last_label`**: Returns the last label of the context, or `None` if the `labels` dictionary is empty.

* **`last_response`**: Returns the last response of the context, or `None` if the `responses` dictionary is empty.

* **`last_response` (setter) and `last_request` (setter)**: These methods allow you to set the last response or request for the current context, which is useful for working with response and request wrappers.

* **`current_node`**: Returns the current node of the context. This is particularly useful for tracking the node during the conversation flow.

* **`overwrite_current_node_in_processing(processed_node: Node)`**: This method allows you to overwrite the current node with a processed node, but it can only be used within processing functions.

Serialization
~~~~~~~~~~~~~

The fact that the `Context` class is a Pydantic model makes it easily convertible to other data formats,
such as JSON. For instance, as a developer, you don't need to implement instructions on how datetime fields
need to be marshalled, since this functionality is provided by Pydantic out of the box.
As a result, working with web interfaces and databases that require the transmitted data to be serialized
becomes as easy as calling the `model_dump_json` method:

.. code-block:: python

    context = Context()
    serialized_context = context.model_dump_json()

Knowing that, you can easily extend DFF to work with storages like Memcache or web APIs of your liking.