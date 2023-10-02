Context guide
--------------

Introduction
~~~~~~~~~~~~

A Context is a data structure that is used to store information about the current state of a conversation.
It is used to keep track of the user's input, the current stage of the conversation, and any other
information that is relevant to the current context of a dialog.
The Context provides a convenient interface for working with data, allowing developers to easily add,
retrieve, and manipulate data as the conversation progresses.

**Serialization**

The fact that the `Context` class is a Pydantic model makes it easily convertible to other data formats,
such as JSON. For instance, as a developer, you don't need to implement instructions on how datetime fields
need to be marshalled, since this functionality is provided by Pydantic out of the box.
As a result, working with web interfaces and databases that require the transmitted data to be serialized
becomes as easy as calling the `model_dump_json` method:

.. code:: python

    context = Context()
    serialized_context = context.model_dump_json()

Knowing that, you can easily extend DFF to work with storages like Memcache or web APIs of your liking.