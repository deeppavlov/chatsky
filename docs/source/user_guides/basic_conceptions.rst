Basic Concepts
--------------

Introduction
~~~~~~~~~~~~

Dialog Flow Framework helps its users create conversational services, which is done by
defining a specialized dialog graph that dictates the behaviour of the dialog service.
This dialog graph essentially represents the dialog script that guides the conversation
between the chat-bot and the user.

DFF leverages a specialized language known as a Domain-Specific Language (DSL)
to enable developers to quickly write and comprehend dialog graphs.
This DSL greatly simplifies the process of designing complex conversations and handling
various user inputs, making it easier to build sophisticated conversational systems.

DFF installation and requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For this very basic tutorial we will need only the core dependencies of DFF.
They can be installed via the following command:

.. code-block:: shell

    pip3 install dff

Example conversational chat-bot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let us go through the creation of a simple bot that would play (virtual) ping-pong game with its users.
It would also greet them and handle exceptions.
First, we define the chat-bot in pseudo language:

.. code-block:: text

    If user writes "Hello!":
        Respond with "Hi! Let's play ping-pong!"
        If user writes something else:
            Respond with "You should've started the dialog with 'Hello!'"
            Repeat from responding with "Hi! Let's play ping-pong!" if user writes anything
    
    If user afterwards writes "Ping" or "ping" or "Ping!" or "ping!":
        Respond with "Pong!"
        Repeat this behaviour
        If user writes something else:
            Respond with "You should've written 'Ping', not '[USER MESSAGE]'!"
            Repeat from responding with "Hi! Let's play ping-pong!" if user writes anything

Later in this tutorial we will create this chat-bot using DFF, starting from the very basics
and then elaborating on more complicated topics.

Example chat-bot graph
~~~~~~~~~~~~~~~~~~~~~~

Let's start from creating the very simple dialog agent:

.. code-block:: python

    from dff.pipeline import Pipeline
    from dff.script import TRANSITIONS, RESPONSE, Message
    import dff.script.conditions as cnd

    ping_pong_script = {
        "ping_pong_flow": {
            "start_node": {
                RESPONSE: Message(),
                TRANSITIONS: {
                    "greeting_node": cnd.exact_match(Message(text="Hello!")),
                },
            },
            "greeting_node": {
                RESPONSE: Message(text="Hi! Let's play ping-pong!"),
                TRANSITIONS: {
                    "response_node": cnd.exact_match(Message(text="Ping!")),
                },
            },
            "response_node": {
                RESPONSE: Message(text="Pong!"),
                TRANSITIONS: {
                    "response_node": cnd.exact_match(Message(text="Ping!")),
                },
            },
            "fallback_node": {
                RESPONSE: Message(text="That was against the rules!"),
                TRANSITIONS: {
                    "greeting_node": cnd.true(),
                },
            },
        },
    }

    pipeline = Pipeline.from_script(
        ping_pong_script,
        start_label=("ping_pong_flow", "start_node"),
        fallback_label=("ping_pong_flow", "fallback_node"),
    )

    if __name__ == "__main__":
        pipeline.run()

.. warning::

    Current dialog agent doesn't support different cases and/or marks in "Ping"
    messages, it only supports exact "Ping!" message from user.
    It also supports only one standard error message for any error.

That's what the agent consists of:

* ``ping_pong_script``: in order to create a dialog agent, a dialog **script** is needed;
  a script is a dictionary, where the keys are the names of the flows (that are "sub-dialogs",
  used to separate the whole dialog into multiple sub-dialogs).

* ``ping_pong_flow`` is our behaviour flow; flow is a separated dialog, containing linked
  conversation nodes and possibly some extra data, transitions, etc.

* ``start_node`` is the initial node, contains no response, only transfers user to an other node
  according to the first message user sends.
  It transfers user to ``greeting_node`` if user writes text message exactly equal to "Hello!".

* Each node contains "RESPONSE" and "TRANSITIONS" elements.

* ``RESPONSE`` value should be a ``Message`` object, that can contain text, images,
  audios, attachments, etc.

* ``TRANSITIONS`` value should be a dict, containing node names and conditions,
  that should be met in order to go to the node specified.
  Here, we can see two different types of transitions: ``exact_match`` requires user message text to
  match the provided text exactly, while ``true`` allowes unconditional transition.

* ``greeting_node`` is the node that will greet user and propose him a ping-pong game.
  It transfers user to ``response_node`` if user writes text message exactly equal to "Ping!".

* ``response_node`` is the node that will play ping-pong game with the user.
  It transfers user to ``response_node`` if user writes text message exactly equal to "Ping!".

* ``fallback_node`` is an "exception handling node"; user will be transferred here if in any node
  no transition for the message given by user is found.
  It transfers user to ``greeting_node`` no matter what user writes.

* ``pipeline`` is a special object that processes user requests according to provided script.
  In order to create pipeline, the script should be provided and two two-string tuples:
  the first specifies initial node flow and name and the second (optional) specifies fallback
  node flow and name (if not provided it equals to the first one by default). 

.. note::

    See `tutorial on basic dialog structure`_.

Advanced graph features
~~~~~~~~~~~~~~~~~~~~~~~

Right now the agent we have created is a very simple one and does not behave **exactly** as we wanted
our bot to behave. Let's see how we can improve our script:

.. code-block:: python

    from dff.pipeline import Pipeline
    from dff.script import TRANSITIONS, RESPONSE, Context, Message
    import dff.script.conditions as cnd
    import dff.script.labels as lbl

    def get_previous_node_name(ctx: Context) -> str:
        """
        Get name of the previous visited script node.
        """
        last_label = sorted(list(ctx.labels))[-2] if len(ctx.labels) >= 2 else None
        # labels store the list of nodes the bot transitioned to,
        # so the second to last label would be the label of a previous node
        return ctx.labels[last_label][1] if last_label is not None else "start_node"
        # label is a two-item tuple used to identify a node,
        # the first element is flow name and the second is node name

    def fallback_response(ctx: Context, _: Pipeline, *args, **kwargs) -> Message:
        """
        Generate response for fallback node, according to the previous node
        we have been to.
        If the previous node was `start_node`, a sample message will be returned,
        otherwise the message will include user input.
        """
        if get_previous_node_name(ctx) == "start_node":
            return Message(text="You should've started the dialog with 'Hello!'")
        elif ctx.last_request is not None:
            last_request = ctx.last_request.text
            note = f"You should've written 'Ping', not '{last_request}'!"
            return Message(text=f"That was against the rules! {note}")
        else:
            raise RuntimeError("Error occurred: last request is None!")
            

    ping_pong_script = {
        "ping_pong_flow": {
            "start_node": {
                RESPONSE: Message(),
                TRANSITIONS: {
                    lbl.forward(): cnd.exact_match(Message(text="Hello!")),
                },
            },
            "greeting_node": {
                RESPONSE: Message(text="Hi! Let's play ping-pong!"),
                TRANSITIONS: {
                    lbl.forward(): cnd.regexp(r"^[P|p]ing!?$"),
                },
            },
            "ping_pong_node": {
                RESPONSE: Message(text="Pong!"),
                TRANSITIONS: {
                    lbl.repeat(): cnd.regexp(r"^[P|p]ing!?$"),
                },
            },
            "fallback_node": {
                RESPONSE: fallback_response,
                TRANSITIONS: {
                    "greeting_node": cnd.true(),
                },
            },
        },
    }

    pipeline = Pipeline.from_script(
        ping_pong_script,
        start_label=("ping_pong_flow", "start_node"),
        fallback_label=("ping_pong_flow", "fallback_node"),
    )

    if __name__ == "__main__":
        pipeline.run()

That's what we've changed:

* ``fallback_node`` has a callback response, it prints different messages depending on the
  previous node.

.. note::

    See `tutorial on response functions`_.

* A special function ``get_previous_node_name`` was written to determine the name of the previous
  visited node. It utilizes ``labels`` attribute of the ``Context`` object.

.. note::

    See `documentation of Context object`_.

* Transitions were changed: transitions to next, previous and current node were replaced with special
  standard transitions.

.. note::

    See `tutorial on transitions`_.

* Conditions were changed: now regular expressions are used to check user text input value.

.. note::

    See `tutorial on conditions`_.

Further exploration
~~~~~~~~~~~~~~~~~~~

There are still a lot of capabilities of Dialog Flow Framework that remain uncovered by this tutorial.

For example:

* You can use ``GLOBAL`` transitions that will be available from every node in your script.
  See `tutorial on global transitions`_.

* You can serialize context (available on every transition and response)
  to json or dictionary in order to debug it or extract some values.
  See `tutorial on context serialization`_.

* You can alter user input and modify generated responses.
  User input can be altered with ``PRE_RESPONSE_PROCESSING`` and will happen **before** response generation.
  See `tutorial on pre-response processing`_.
  Node response can be modified with ``PRE_TRANSITION_PROCESSING`` and will happen **after** response generation.
  See `tutorial on pre-transition processing`_.

* Additional data ``MISC`` can be added to every node, flow and script itself.
  Warning! Unlike the other Context fields, the MISC values are not shared across script executions.
  See `tutorial on script MISC`_.

Conclusion
~~~~~~~~~~

In this tutorial, we explored the basics of Dialog Flow Framework (DFF) to build dynamic conversational services.
By using DFF's intuitive Domain-Specific Language (DSL) and well-structured dialog graphs, we created a simple interaction between user and chat-bot.
We covered installation, understanding the DSL and building dialog graph.
However, this is just the beginning. DFF offers a world of possibilities in conversational chat-bot.
With practice and exploration of advanced features, you can create human-like conversations and reach a wider audience by integrating with various platforms.
Now, go forth, unleash your creativity, and create captivating conversational services with DFF.
Happy building!


.. _tutorial on basic dialog structure: https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.1_basics.html
.. _tutorial on response functions: https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.3_responses.html
.. _documentation of Context object: https://deeppavlov.github.io/dialog_flow_framework/apiref/dff.script.core.context.html
.. _tutorial on transitions: https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.4_transitions.html
.. _tutorial on conditions: https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.2_conditions.html
.. _tutorial on global transitions: https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.5_global_transitions.html
.. _tutorial on context serialization: https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.6_context_serialization.html
.. _tutorial on pre-response processing: https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.7_pre_response_processing.html
.. _tutorial on pre-transition processing: https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.9_pre_transitions_processing.html
.. _tutorial on script MISC: https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.8_misc.html
