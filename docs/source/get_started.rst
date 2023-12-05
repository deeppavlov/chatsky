Getting started
---------------

Installation
~~~~~~~~~~~~

DFF can be easily installed on your system using the ``pip`` package manager:

.. code-block:: console
   
   pip install dff

This framework is compatible with Python 3.8 and newer versions.

The above command will set the minimum dependencies to start working with DFF. 
The installation process allows the user to choose from different packages based on their dependencies, which are:

.. code-block:: console

   pip install dff[json]  # dependencies for using JSON
   pip install dff[pickle] # dependencies for using Pickle
   pip install dff[redis]  # dependencies for using Redis
   pip install dff[mongodb]  # dependencies for using MongoDB
   pip install dff[mysql]  # dependencies for using MySQL
   pip install dff[postgresql]  # dependencies for using PostgreSQL
   pip install dff[sqlite]  # dependencies for using SQLite
   pip install dff[ydb]  # dependencies for using Yandex Database
   pip install dff[telegram]  # dependencies for using Telegram
   pip install dff[benchmark]  # dependencies for benchmarking

For example, if you are going to use one of the database backends,
you can specify the corresponding requirements yourself.

Additionally, you also have the option to download the source code directly from the
`GitHub <https://github.com/deeppavlov/dialog_flow_framework>`_ repository using the commands:

.. code-block:: console

   git clone https://github.com/deeppavlov/dialog_flow_framework.git
   cd dialog_flow_framework

Once you are in the directory, you can run the command ``make venv`` to set up all the necessary requirements for the library.
If you need to update the requirements, use the command ``make clean`` to remove `venv` first.

Key concepts
~~~~~~~~~~~~

DFF is a powerful tool for creating conversational services.
It allows developers to easily write and manage dialog systems by defining a special
dialog graph that describes the behavior of the service.
DFF offers a specialized language (DSL) for quickly writing dialog graphs,
making it easy for developers to create chatbots for a wide
range of applications, such as social networks, call centers, websites, personal assistants, etc.

DFF has several important concepts:

**Script**: First of all, to create a dialog agent it is necessary
to create a dialog :py:class:`~dff.script.core.script.Script`.
A dialog `script` is a dictionary, where keys correspond to different `flows`.
A script can contain multiple scripts, which are flows too, what is needed in order to divide
a dialog into sub-dialogs and process them separately.

**Flow**: As mentioned above, the dialog is divided into flows.
Each flow represent a sub-dialog corresponding to the discussion of a particular topic.
Each flow is also a dictionary, where the keys are the `nodes`.

**Node**: A `node` is the smallest unit of a dialog flow, and it contains the bot's response
to a user's input as well as a `condition` that determines
the `transition` to another node, whether it's within the current or another flow.

**Keywords**: DFF uses several special `keywords`. These keywords are the keys in the dictionaries inside the script.
The most important for using the framework are `RESPONSE` and `TRANSITIONS` keywords.
The first one corresponds to the response that the bot will send to the user from the current node.
The second corresponds to the transition conditions from the current node to other nodes.