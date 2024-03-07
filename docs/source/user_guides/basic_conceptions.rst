Basic Concepts
--------------

Introduction
~~~~~~~~~~~~

The Dialog Flow Framework (DFF) is a modern tool for designing conversational services.

DFF introduces a specialized Domain-Specific Language (DSL) based on standard Python functions and data structures
which makes it very easy for developers with any level of expertise to design a script for user - bot interaction. 
The script comes in a form of a *dialog graph* where
each node equals a specific state of the dialog, i.e. a specific conversation turn.
The graph includes the majority of the conversation logic, and covers one or several user scenarios, all in a single Python dict.

In this tutorial, we describe the basics of DFF API,
and walk you through the process of creating and maintaining a conversational service with the help of DFF.


Creating Conversational Services with DFF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Installation
============

To get started with DFF, you need to install its core dependencies, which can be done using the following command:

.. code-block:: shell

    pip3 install dff

Defining Dialogue Goals and User Scenarios
==========================================

To create a conversational service using Dialog Flow Framework (DFF), you start by defining the overall dialogue goal 
and breaking down the dialogue into smaller scenarios based on the user intents or actions that you want to cover.
DFF's Domain-Specific Language makes it easy to break down the dialog script into `flows`, i.e. named groups of nodes
unified by a specific purpose.

For instance, if one of the dialog options that we provide to the user is to play a game,
the bot can have a 'game' flow that contains dialog states related to this subject, while other flows
cover other topics, e.g. 'time' flow can include questions and answers related to telling the time,
'weather' to telling the weather, etc.

Creating Dialogue Flows for User Scenarios
==========================================

Once you have DFF installed, you can define dialog flows targeting various user scenarios
and combine them in a global script object. A flow consists of one or more nodes
that represent conversation turns.

.. note::

    In other words, the script object has 3 levels of nestedness:
    **script - flow - node**

Let's assume that the only user scenario of the service is the chat bot playing ping pong with the user.
The practical implementation of this is that the bot is supposed to reply 'pong' to messages that say 'ping'
and handle any other messages as exceptions. The pseudo-code for the said flow would be as follows:

.. code-block:: text

    If user writes "Hello!":
        Respond with "Hi! Let's play ping-pong!"

        If user afterwards writes "Ping" or "ping" or "Ping!" or "ping!":
            Respond with "Pong!"
            Repeat this behaviour

    If user writes something else:
        Respond with "That was against the rules"
        Go to responding with "Hi! Let's play ping-pong!" if user writes anything

This leaves us with a single dialog flow in the dialog graph that we lay down below, with the annotations for
each part of the graph available under the code snippet.

Example flow & script
=====================

.. code-block:: python
    :linenos:

    from dff.pipeline import Pipeline
    from dff.script import TRANSITIONS, RESPONSE, Message
    import dff.script.conditions as cnd

    ping_pong_script = {
        "greeting_flow": {
            "start_node": {
                RESPONSE: Message(),  # the response of the initial node is skipped
                TRANSITIONS: {
                    ("greeting_flow", "greeting_node"):
                        cnd.exact_match(Message("/start")),
                },
            },
            "greeting_node": {
                RESPONSE: Message("Hi!"),
                TRANSITIONS: {
                    ("ping_pong_flow", "game_start_node"):
                        cnd.exact_match(Message("Hello!"))
                }
            },
            "fallback_node": {
                RESPONSE: fallback_response,
                TRANSITIONS: {
                    ("greeting_flow", "greeting_node"): cnd.true(),
                },
            },
        },
        "ping_pong_flow": {
            "game_start_node": {
                RESPONSE: Message("Let's play ping-pong!"),
                TRANSITIONS: {
                    ("ping_pong_flow", "response_node"):
                        cnd.exact_match(Message("Ping!")),
                },
            },
            "response_node": {
                RESPONSE: Message("Pong!"),
                TRANSITIONS: {
                    ("ping_pong_flow", "response_node"):
                        cnd.exact_match(Message("Ping!")),
                },
            },
        },
    }

    pipeline = Pipeline.from_script(
        ping_pong_script,
        start_label=("greeting_flow", "start_node"),
        fallback_label=("greeting_flow", "fallback_node"),
    )

    if __name__ == "__main__":
        pipeline.run()

The code snippet defines a script with a single dialogue flow that emulates a ping-pong game.
Likewise, if additional scenarios need to be covered, additional flow objects can be embedded into the same script object.

* ``ping_pong_script``: The dialog **script** mentioned above is a dictionary that has one or more
  dialog flows as its values.

* ``ping_pong_flow`` is the game emulation flow; it contains linked
  conversation nodes and possibly some extra data, transitions, etc.

* A node object is an atomic part of the script.
  The required fields of a node object are ``RESPONSE`` and ``TRANSITIONS``.

* The ``RESPONSE`` field specifies the response that the dialog agent gives to the user in the current turn.

* The ``TRANSITIONS`` field specifies the edges of the dialog graph that link the dialog states.
  This is a dictionary that maps labels of other nodes to conditions, i.e. callback functions that
  return `True` or `False`. These conditions determine whether respective nodes can be visited
  in the next turn.
  In the example script, we use standard transitions: ``exact_match`` requires the user request to
  fully match the provided text, while ``true`` always allows a transition. However, passing custom
  callbacks that implement arbitrary logic is also an option.

* ``start_node`` is the initial node, which contains an empty response and only transfers user to another node
  according to the first message user sends.
  It transfers user to ``greeting_node`` if user writes text message exactly equal to "Hello!".

* ``greeting_node`` is the node that will greet user and propose him a ping-pong game.
  It transfers user to ``response_node`` if user writes text message exactly equal to "Ping!".

* ``response_node`` is the node that will play ping-pong game with the user.
  It transfers user to ``response_node`` if user writes text message exactly equal to "Ping!".

* ``fallback_node`` is an "exception handling node"; user will be transferred here if
  none of the transition conditions (see ``TRANSITIONS``) is satisfied.
  It transfers user to ``greeting_node`` no matter what user writes.

* ``pipeline`` is a special object that traverses the script graph based on the values of user input.
  It is also capable of executing custom actions that you want to run on every turn of the conversation.
  The pipeline can be initialized with a script, and with labels of two nodes:
  the entrypoint of the graph, aka the 'start node', and the 'fallback node'
  (if not provided it defaults to the same node as 'start node').

.. note::

    See `tutorial on basic dialog structure <../tutorials/tutorials.script.core.1_basics.html>`_.

Processing Definition
=====================

.. note::

    The topic of this section is explained in greater detail in the following tutorials:

    * `Pre-response processing <../tutorials/tutorials.script.core.7_pre_response_processing.html>`_
    * `Pre-transitions processing <../tutorials/tutorials.script.core.9_pre_transitions_processing.html>`_
    * `Pipeline processors <../tutorials/tutorials.pipeline.2_pre_and_post_processors.html>`_

Processing user requests and extracting additional parameters is a crucial part of building a conversational bot. 
DFF allows you to define how user requests will be processed to extract additional parameters.
This is done by passing callbacks to a special ``PROCESSING`` fields in a Node dict.

* User input can be altered with ``PRE_RESPONSE_PROCESSING`` and will happen **before** response generation. See `tutorial on pre-response processing`_.
* Node response can be modified with ``PRE_TRANSITIONS_PROCESSING`` and will happen **after** response generation but **before** transition to the next node. See `tutorial on pre-transition processing`_.

Depending on the requirements of your bot and the dialog goal, you may need to interact with external databases or APIs to retrieve data. 
For instance, if a user wants to know a schedule, you may need to access a database and extract parameters such as date and location.

.. code-block:: python

    import requests
    ...
    def use_api_processing(ctx: Context, _: Pipeline):
        # save to the context field for custom info
        ctx.misc["api_call_results"] = requests.get("http://schedule.api/day1").json()
    ...
    node = {
        RESPONSE: ...
        TRANSITIONS: ...
        PRE_TRANSITIONS_PROCESSING: {"use_api": use_api_processing}
    }

.. note::

    This function uses ``Context`` to store the result of a request for other functions to use.
    Context is a data structure that keeps all the information about a specific conversation.

    To learn more about ``Context`` see the `relevant guide <../user_guides/context_guide.html>`__.

If you retrieve data from the database or API, it's important to validate it to ensure it meets expectations.

Since DFF extensively leverages pydantic, you can resort to the validation tools of this feature-rich library.
For instance, given that each processing routine is a callback, you can use tools like pydantic's `validate_call`
to ensure that the returned values match the function signature.
Error handling logic can also be incorporated into these callbacks.

Generating a bot Response
=========================

Generating a bot response involves creating a text or multimedia response that will be delivered to the user.
Response is defined in the ``RESPONSE`` section of each node and should be either a ``Message`` object,
that can contain text, images, audios, attachments, etc., or a callback that returns a ``Message``.
The latter allows you to customize the response based on the specific scenario and user input.

.. code-block:: python

    def sample_response(ctx: Context, _: Pipeline) -> Message:
        if ctx.misc["user"] == 'vegan':
            return Message("Here is a list of vegan cafes.")
        return Message("Here is a list of cafes.")

Handling Fallbacks
==================

In DFF, you should provide handling for situations where the user makes requests
that do not trigger any of the transitions specified in the script graph. 
To cover that use case, DFF requires you to define a fallback node that the agent will move to
when no adequate transition has been found.

Like other nodes, the fallback node can either use a message or a callback to produce a response
which gives you a lot of freedom in creating situationally appropriate error messages.
Create friendly error messages and, if possible, suggest alternative options. 
This ensures a smoother user experience even when the bot encounters unexpected inputs.

.. code-block:: python

    def fallback_response(ctx: Context, _: Pipeline) -> Message:
        """
        Generate a special fallback response depending on the situation.
        """
        if ctx.last_request is not None:
            if ctx.last_request.text != "/start" and ctx.last_label is None:
                # an empty last_label indicates start_node
                return Message("You should've started the dialog with '/start'")
            else:
                return Message(
                    text=f"That was against the rules!\n"
                         f"You should've written 'Ping', not '{ctx.last_request.text}'!"
                )
        else:
            raise RuntimeError("Error occurred: last request is None!")

Testing and Debugging
~~~~~~~~~~~~~~~~~~~~~

Periodically testing the conversational service is crucial to ensure it works correctly.
You should also be prepared to debug the code and dialogue logic if problems are discovered during testing. 
Thorough testing helps identify and resolve any potential problems in the conversation flow.

The basic testing procedure offered by DFF is end-to-end testing of the pipeline and the script
which ensures that the pipeline yields correct responses for any given input.
It requires a sequence of user request - bot response pairs that form the happy path of your
conversational service.

.. code-block:: python

    happy_path = (
        (Message("/start"), Message("Hi!")),
        (Message("Hello!"), Message("Let's play ping-pong!")),
        (Message("Ping!"), Message("Pong!"))
    )

A special function is then used to ascertain complete identity of the messages taken from
the happy path and the pipeline. The function will play out a dialog with the pipeline acting as a user while checking returned messages.

.. code-block:: python

    from dff.utils.testing.common import check_happy_path

    check_happy_path(pipeline, happy_path)

Monitoring and Analytics
~~~~~~~~~~~~~~~~~~~~~~~~

Setting up bot performance monitoring and usage analytics is essential to monitor its operation and identify potential issues. 
Monitoring helps you understand how users are interacting with the bot and whether any improvements are needed.
Analytics data can provide valuable insights for refining the bot's behavior and responses.

DFF provides a `statistics` module as an out-of-the-box solution for collecting arbitrary statistical metrics
from your service. Setting up the data collection is as easy as instantiating the relevant class in the same
context with the pipeline. 
What's more, the data you obtain can be visualized right away using Apache Superset as a charting engine.

.. note::

    More information is available in the respective `guide <../user_guides/superset_guide.html>`__.

Iterative Improvement
~~~~~~~~~~~~~~~~~~~~~

To continually enhance your chat-bot's performance, monitor user feedback and analyze data on bot usage.
For instance, the statistics or the charts may reveal that some flow is visited by users more frequently or
less frequently than planned. This would mean that adjustments to the transition structure
of the graph need to be made.

Gradually improve the transition logic and response content based on the data received. 
This iterative approach ensures that the bot becomes more effective over time.

Data Protection
~~~~~~~~~~~~~~~

Data protection is a critical consideration in bot development, especially when handling sensitive information.

.. note::

    The DFF framework helps ensure the safety of your application by storing the history and other user data present
    in the ``Context`` object under unique ids and abstracting the storage logic away from the user interface.
    As a result, it offers the basic level of data protection making it impossible to gain unlawful access to personal information.

Documentation
~~~~~~~~~~~~~

Creating documentation is essential for teamwork and future bot maintenance. 
Document how different parts of the script work and how the bot covers the expected interaction scenarios.
It is especially important to document the purpose and functionality of callback functions and pipeline services
that you may have in your project, using Python docstrings.

.. code-block:: python

    def fav_kitchen_response(ctx: Context, _: Pipeline) -> Message:
        """
        This function returns a user-targeted response depending on the value
        of the 'kitchen preference' slot.
        """
        ...

This documentation serves as a reference for developers involved in the project.

Scaling
~~~~~~~

If your bot becomes popular and requires scaling, consider scalability during development.
Scalability ensures that the bot can handle a growing user base without performance issues.
While having only one application instance will suffice in most cases, there are many ways
how you can adapt the application to a high load environment.

* With the database connection support that DFF offers out of the box, DFF projects can be easily scaled through sharing the same database between multiple application instances. However, using an external database is required due to the fact that this is the only kind of storage that can be efficiently shared between processes.
* Likewise, using multiple database instances to ensure the availability of data is also an option.
* The structure of the `Context` object makes it easy to vertically partition the data storing different subsets of data across multiple database instances.

Further reading
~~~~~~~~~~~~~~~

* `Tutorial on basic dialog structure <../tutorials/tutorials.script.core.1_basics.html>`_
* `Tutorial on transitions <../tutorials/tutorials.script.core.4_transitions.html>`_
* `Tutorial on conditions <../tutorials/tutorials.script.core.2_conditions.html>`_
* `Tutorial on response functions <../tutorials/tutorials.script.core.3_responses.html>`_
* `Tutorial on pre-response processing <../tutorials/tutorials.script.core.7_pre_response_processing.html>`_
* `Tutorial on pre-transition processing <../tutorials/tutorials.script.core.9_pre_transitions_processing.html>`_
* `Guide on Context <../user_guides/context_guide.html>`_
* `Tutorial on global transitions <../tutorials/tutorials.script.core.5_global_transitions.html>`_
* `Tutorial on context serialization <../tutorials/tutorials.script.core.6_context_serialization.html>`_
* `Tutorial on script MISC <../tutorials/tutorials.script.core.8_misc.html>`_