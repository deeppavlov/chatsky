API reference
-------------

.. toctree::
   :name: reference
   :glob:
   :maxdepth: 1

   apiref/index_*


   
Context Storages
~~~~~~~~~~~~~~~~

Context Storages allow you to save and retrieve user dialogue states
(in the form of a `Context` object) using various database backends. 
The following backends are currently supported:

- **Redis:** Provides a Redis-based version of the :py:class:`.DBContextStorage` class.

- | **Protocol:** This module contains base protocol code. Supported protocols fot db:
    shelve, json, pickle, sqlite, redis, mongodb, mysql, postgresql, grpc, grpcs.

- | **SQL:** Provides a SQL-based version of the DBContextStorage class.
    It allows the user to choose the backend option of his liking from MySQL, PostgreSQL, or SQLite.

- **Mongo:** Provides a MongoDB-based version of the DBContextStorage class.

- **JSON:** Provides a JSON-based version of the DBContextStorage class.

- **Pickle:** Provides a pickle-based version of the DBContextStorage class.

- **Database:** This module contains the Database class which is used to store and retrieve context data.

- **Shelve:** Provides a shelve-based version of the DBContextStorage class.

- | **Yandex DB:** Provides a version of the DBContextStorage class that is specifically designed
    to work with Yandex DataBase.


Messenger Interfaces
~~~~~~~~~~~~~~~~~~~~

- | **Message Interfaces:** This module contains several basic classes of message interfaces.
    These classes provide a standardized way of interacting with different messaging services,
    allowing the application to work with multiple messaging platforms seamlessly.

- | **Telegram interface:** This package contains classes and functions specific
    to the Telegram messenger service. It provides an interface for the application to interact with Telegram,
    allowing it to send and receive messages, handle callbacks, and perform other actions.

- | **Types:** This module contains special types that are used for the messenger interface to client interaction.
    These types are used to define the format of messages and other data that is exchanged between the
    application and the messaging service.


Pipeline
~~~~~~~~

- | **Conditions:** The conditions module contains functions that can be used to determine whether the pipeline
    component to which they are attached should be executed or not.

- | **Service Group:** This module contains the :py:class:`.ServiceGroup` class. This class represents a group
    of services that can be executed together in a specific order.

- **Component:** This module contains the :py:class:`.PipelineComponent` class, which can be group or a service.

- | **Pipeline:** This module contains the :py:class:`.Pipeline` class. This class represents the main pipeline of
    the DFF and is responsible for managing the execution of services.

- | **Service:** This module contains the :py:class:`.Service` class,
    which can be included into pipeline as object or a dictionary.

Script
~~~~~~

- | **dff.script.extras.slots package:** This package contains classes and functions specific to the use of slots
    in a dialog script.

- | **Conditions:** This module contains a standard set of scripting conditions that
    can be used to control the flow of a conversation.

- | **Message:** This module contains a universal response model that is supported in `DFF`.
    It only contains types and properties that are compatible with most messaging services and
    can support service-specific UI models.

- | **dff.script.extras.conditions package:** This package contains additional classes and functions that can be used
    to define and check conditions in a dialog script.

- | **Types:** This module contains basic types that are used throughout the `DFF`.
    These types include classes and special types that are used to define the structure of data and the behavior
    of different components in the pipeline.

- | **Script:** This module contains a set of pydantic models for the dialog graph. These models define the structure
    of a dialog script.

- | **Keywords:** This module contains a set of keywords that are used to define the dialog graph.
    These keywords are used to specify the structure and behavior of a script,
    such as the nodes and edges of the graph, and can be used to create custom scripts.

- | **Responses:** This module contains a set of standard responses that can be used in a dialog script.
    These responses can be used to specify the text, commands, attachments, and other properties
    of a message that will be sent to the user.

- | **Context:** This module contains the :py:class:`.Context` class, which is used for the context storage.
    It provides a convenient interface for working with data, adding data, data serialization, type checking ,etc.

- | **Labels:** This module contains labels that define the target name of the transition node.

- | **Actor:** This module contains the :py:class:`.Actor` class.
    It is one of the main abstractions that processes incoming requests
    from the user in accordance with the dialog graph.

- **Normalization:** This module contains a basic set of functions for normalizing data in a dialog script.
