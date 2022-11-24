.. Dialog Flow Framework documentation master file, created by
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

dialog flow framework's documentation
=====================================

*Date*: 29.11.2022 *Version*: 1.0.0

The Dialog Flow Framework's (DFF) is an open-source Apache 2.0-licensed library developed for creating dialog systems.

Getting started
---------------

Installation
~~~~~~~~~~~~

`DFF` can be installed via `pip`:

.. code-block:: bash

   pip install dff

or download from `Github <https://github.com/deeppavlov/dialog_flow_framework>`_:

.. code-block:: bash

   git clone https://github.com/deeppavlov/dialog_flow_framework.git
   make clean
   make venv

The last command will set up all requirements.

Key concepts
~~~~~~~~~~~~

DFF allows you to write conversational services. The service is written by defining a special dialog graph
that describes the behavior of the dialog service. The dialog graph contains the dialog script.
DFF offers a specialized language (DSL) for quickly writing dialog graphs.
You can use it to write chatbots for social networks, call centers, websites, writing skills for Amazon Alexa, etc.

DFF has the following important concepts:

**Script**: First of all, to create a dialog agent it is necessary to create a dialog (:py:class:`~dff.core.engine.core.script.Script`).
A dialog script is a dictionary, where keys correspond to different `flows`.
Script is needed to separate a dialog into sub-dialogs. Processes in sub-dialogs are separately.

**Flow**: As mentioned above, the dialogue is divided into `flows`.
Each `flow` represent a sub-dialogue corresponding to the discussion of a particular topic.
Each `flow` is also a dictionary, where the keys are the `nodes`.

**Node**: Each `node` necessarily contains a `RESPONSE` of the bot and the `CONDITIONS` of `TRANSITION` to another `node`
in this or another `flow`.


.. toctree::
   :caption: Contents:


.. toctree::
   :caption: Documentation
   :name: documentation
   :maxdepth: 4
   :glob:

   apiref/modules


.. toctree::
   :caption: Examples
   :name: rst-gallery
   :maxdepth: 3
   :glob:
   :reversed:

   examples/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
