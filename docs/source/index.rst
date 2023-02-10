.. Dialog Flow Framework documentation master file, created by
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Dialog Flow Framework Documentation
=====================================

*Date*: |today| *Version*: |version|

The Dialog Flow Framework (`DFF`) is an open-source, `Apache 2.0 <https://www.apache.org/licenses/LICENSE-2.0>`_-licensed library
that was developed specifically for creating dialog systems. `DFF` provides a comprehensive set of tools and resources for building conversational systems
for a wide range of applications, including chatbots, virtual assistants, and other interactive systems.
It allows developers to easily create and manage complex dialog flows, integrate with natural language processing (NLP) tools,
and handle user input in a flexible and efficient manner. Additionally, the framework is highly customizable,
allowing developers to easily adapt it to their specific needs and requirements. 

Getting started
---------------

Installation
~~~~~~~~~~~~

`DFF` can be easily installed on your system using the ``pip`` package manager:

.. code-block:: console
   
   pip install dff

This framework is compatible with Python 3.7 and newer versions.
Note that if you are going to use one of the database backends, you will have to specify an extra or install the corresponding requirements yourself.
Additionally, you also have the option to download the source code directly from the
`GitHub <https://github.com/deeppavlov/dialog_flow_framework>`_ repository using the commands:

.. code-block:: console

   git clone https://github.com/deeppavlov/dialog_flow_framework.git
   cd dialog_flow_framework

Once you are in the directory, you can run the command ``make venv`` to set up all the necessary requirements for the library.
If you need to update the requirements, use the command ``make clean`` to remove `venv` first.

Key concepts
~~~~~~~~~~~~

`DFF` is a powerful tool for creating conversational services.
It allows developers to easily write and manage dialog systems by defining a special dialog graph that describes the behavior of the service.
`DFF` offers a specialized language (`DSL`) for quickly writing dialog graphs, making it easy for developers to create chatbots for a wide
range of applications such as social networks, call centers, websites, skills for Amazon Alexa, etc.

`DFF` has several important concepts:

**Script**: First of all, to create a dialog agent it is necessary to create a dialog (:py:class:`~dff.script.core.script.Script`).
A dialog `script` is a dictionary, where keys correspond to different `flows`. A script can contain multiple `scripts`, what is needed in order to divide
a dialog into sub-dialogs and process them separately.

**Flow**: As mentioned above, the dialog is divided into `flows`.
Each `flow` represent a sub-dialog corresponding to the discussion of a particular topic.
Each `flow` is also a dictionary, where the keys are the `nodes`.

**Node**: A `node` is the smallest unit of a dialog `flow`, and it contains the bot's response to a user's input as well as a `condition` that determines
the `transition` to another `node`, whether it's within the current or another `flow`.

ToCs
----

Context Storages
~~~~~~~~~~~~~~~~

- **Redis:** Provides a Redis-based version of the :py:class:`.DBContextStorage` class.

- **Protocol:** This module contains base protocol code. Supported protocols fot db:
   shelve, json, pickle, sqlite, redis, mongodb, mysql, postgresql, grpc, grpcs.

- **SQL:** Provides a SQL-based version of the :py:class:`.DBContextStorage` class.
   It allows the user to choose the backend option of his liking from MySQL, PostgreSQL, or SQLite.

- **Mongo:** Provides a MongoDB-based version of the :py:class:`.DBContextStorage` class.

- **JSON:** Provides a json-based version of the :py:class:`.DBContextStorage` class.

- **Pickle:** Provides a pickle-based version of the :py:class:`.DBContextStorage` class.

- **Database:** This module contains the Database class which is used to store and retrieve context data.

- **Shelve:** Provides a shelve-based version of the :py:class:`.DBContextStorage` class.

- **Yandex DB:** Provides a version of the :py:class:`.DBContextStorage` class that is specifically designed
   to work with Yandex DataBase.


Messenger Interfaces
~~~~~~~~~~~~~~~~~~~~

- **Message Interfaces:** This module contains several basic classes of message interfaces.
   These classes provide a standardized way of interacting with different messaging services,
   allowing the application to work with multiple messaging platforms seamlessly.

- **dff.messengers.telegram package:** This package contains classes and functions specific
   to the Telegram messenger service. It provides an interface for the application to interact with Telegram,
   allowing it to send and receive messages, handle callbacks, and perform other actions.

- **Types:** This module contains special types that are used for the messenger interface to client interaction.
   These types are used to define the format of messages and other data that is exchanged between the
   application and the messaging service.


Pipeline
~~~~~~~~

- **Conditions:** The conditions module contains functions that can be used to determine whether the pipeline
   component to which they are attached should be executed or not.

- **Service Group:** This module contains the :py:class:`.ServiceGroup` class. This class represents a group
   of services that can be executed together in a specific order.

- **Utils:** This module contains several utility functions that are used to perform various
   tasks such as data processing, error handling, and debugging.

- **Component:** This module contains the :py:class:`.PipelineComponent` class, which can be group or a service.

- **Extra Handler:** This module contains an extra handlers that can be used to handle additional
   functionality or features that are not included in the standard pipeline classes.

- **Pipeline:** This module contains the :py:class:`.Pipeline` class. This class represents the main pipeline of
   the `DFF` and is responsible for managing the execution of services.

- **Service:** This module contains the :py:class:`.Service` class,
   which can be included into pipeline as object or a dictionary.

- **Utility Functions:** This module contains several utility functions that are used to perform various
   tasks such as data processing, error handling, and debugging.

- **Types:** This module contains basic types that are used throughout the `DFF`.
   These types include classes and special types that are used to define the structure of data
   and the behavior of different components in the pipeline.

# TODO: remove Utils, Extra Handler, Utility Functions, Type

Script
~~~~~~

- **dff.script.extras.slots package:** This package contains classes and functions specific to the use of slots
   in a dialog script.

- **Conditions:** This module contains a standard set of scripting conditions that
   can be used to control the flow of a conversation.

- **Message:** This module contains a universal response model that is supported in `DFF`.
   It only contains types and properties that are compatible with most messaging services and
   can support service-specific UI models.

- **dff.script.extras.conditions package:** This package contains additional classes and functions that can be used
   to define and check conditions in a dialog script.

- **Types:** This module contains basic types that are used throughout the `DFF`.
   These types include classes and special types that are used to define the structure of data and the behavior
   of different components in the pipeline.

- **Script:** This module contains a set of pydantic models for the dialog graph. These models define the structure
   of a dialog script.

- **Keywords:** This module contains a set of keywords that are used to define the dialog graph.
   These keywords are used to specify the structure and behavior of a script,
   such as the nodes and edges of the graph, and can be used to create custom scripts.

- **Responses:** This module contains a set of standard responses that can be used in a dialog script.
   These responses can be used to specify the text, commands, attachments, and other properties
   of a message that will be sent to the user.

- **Context:** This module contains the :py:class:`.Context` class, which is used for the context storage.
   It provides a convenient interface for working with data, adding data, data serialization, type checking ,etc.

- **Labels:** This module contains labels that define the target name of the transition node.

- **Actor:** This module contains the :py:class:`.Actor` class.
   It is one of the main abstractions that processes incoming requests
   from the user in accordance with the dialog graph.

- **Normalization:** This module contains a basic set of functions for normalizing data in a dialog script.


Documentation and Examples
--------------------------

.. toctree::
   :caption: Documentation
   :name: documentation
   :glob:
   :maxdepth: 1

   apiref/index_*

.. toctree::
   :caption: Examples
   :name: examples
   :glob:

   examples/*/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
