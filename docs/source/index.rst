.. Dialog Flow Framework documentation master file, created by
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Dialog flow framework's documentation
=====================================

*Date*: ??.11.2022 *Version*: 1.0.0

The Dialog Flow Framework's (`DFF`) is an open-source `Apache 2.0 <https://www.apache.org/licenses/LICENSE-2.0>`_-licensed library
developed for creating dialog systems.

Getting started
---------------

Installation
~~~~~~~~~~~~

DFF can be installed via ``pip``:

.. code-block:: bash
   
   pip install dff

You can also download the library from `Github <https://github.com/deeppavlov/dialog_flow_framework>`_:

.. code-block:: bash

   git clone https://github.com/deeppavlov/dialog_flow_framework.git
   cd dialog_flow_framework
   make venv

The last command will set up all requirements. If requirements need to be updated, use the command ``make clean`` before ``make venv``.

Key concepts
~~~~~~~~~~~~

`DFF` allows you to write conversational services. The service is written by defining a special dialog graph
that describes the behavior of the dialog service. `DFF` offers a Specialized Language (`DSL`) for quickly writing dialog graphs.
You can use it to write chatbots for social networks, call centers, websites, writing skills for Amazon Alexa, etc.

DFF has the following important concepts:

**Script**: First of all, to create a dialog agent it is necessary to create a dialog (:py:class:`~dff.core.engine.core.script.Script`).
A dialog `script` is a dictionary, where keys correspond to different `flows`. A script can contain multiple `scripts`, what is needed in order to divide
a dialog into sub-dialogs and process them separately.

**Flow**: As mentioned above, the dialogue is divided into `flows`.
Each `flow` represent a sub-dialogue corresponding to the discussion of a particular topic.
Each `flow` is also a dictionary, where the keys are the `nodes`.

**Node**: Each `node` necessarily contains a `response` of the bot and
the `condition` (:py:class:`~dff.core.engine.conditions`) of `transition` to another `node`
in this or another `flow`.

.. toctree::
   :caption: Documentation
   :maxdepth: 3

   apiref/dff.core
   apiref/dff.connectors

.. toctree::
   :caption: Examples
   :maxdepth: 3
   :reversed:

   examples/pipeline/index
   examples/engine/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
