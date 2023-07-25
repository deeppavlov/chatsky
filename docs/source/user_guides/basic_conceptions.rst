Basic Concepts
--------------

Introduction
~~~~~~~~~~~~

Dialog Flow Framework starts from creating conversational services,
defining a specialized dialog graph that dictates the behavior of the dialog service.
This dialog graph essentially represents the dialog script that guides the conversation
between the AI and the user.

The DFF leverages a specialized language known as a Domain-Specific Language (DSL)
to enable developers to quickly write and comprehend dialog graphs.
This DSL greatly simplifies the process of designing complex conversations and handling
various user inputs, making it easier to build sophisticated conversational systems.

DFF installation and requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For this very basic tutorial we will need only the core dependencies of DFF.
They can be installed via the following command:

.. code-block:: shell

    pip3 install dff

.. note::

    Any python version starting from Python 3.8 is supported by DFF,
    however no tests for versions higher than 3.11 were executed.

Example conversational AI
~~~~~~~~~~~~~~~~~~~~~~~~~

Let us go through creation of a simple bot that would play (virtual) ping-pong game with user.
It will also greet user and handle exceptions.
First, we would define the AI in pseudo language:

.. code-block:: text

    If user writes "Hello!":
        Respond with "Hi! Let's play ping-pong!"
    
    If user afterwards writes "Ping" or "ping" or "Ping!":
        Respond with "Pong!"
        Repeat this behaviour
    
    If user afterwards writes something else:
        Respond with "That was against the rules!"
        Repeat from the beginning if user writes anything

Later in this tutorial we will create this AI using DFF, starting from the very basics
and then elaborating on more complicated topics.

Example AI graph
~~~~~~~~~~~~~~~~

Let's start from creating the very simple dialog agent implementation:

.. code-block:: python

    from dff.pipeline import Pipeline
    from dff.script import TRANSITIONS, RESPONSE, Message
    import dff.script.conditions as cnd
    from dff.utils.testing.common import run_interactive_mode

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
        run_interactive_mode(pipeline)

.. warning::

    Current dialog agent implementation doesn't support different cases and/or marks in "Ping"
    messages, it only supports exact "Ping!" message from user.

That's what the agent consists of:

* ``ping_pong_script`` in order to create a dialog agent, a dialog **script** is needed;
  a script is a dictionary, where the keys are the names of the flows (that are "sub-dialogs",
  used to separate the whole dialog into multiple sub-dialogs).

* ``ping_pong_flow`` is our behaviour flow; flow is a separated dialog, containing linked
  conversation nodes and maybe some extra data, transitions, etc.

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

* ``run_interactive_mode`` is a function for dialog testing, it executes pipeline in a loop,
  using CLI to accept user input and provide user with output.

.. note::

    See :doc:`tutorial on basic dialog structure <https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.1_basics.html>`.

Advanced graph features
~~~~~~~~~~~~~~~~~~~~~~~

Right now the agent we have created is a very simple one and does not behaves **exactly** as we wanted
our bot to behave. Let's elaborate on that and see how can we improve our script:

.. code-block:: python

    from dff.pipeline import Pipeline
    from dff.script import TRANSITIONS, RESPONSE, Context, Message
    import dff.script.conditions as cnd
    import dff.script.labels as lbl
    from dff.utils.testing.common import run_interactive_mode

    def get_previous_node_name(ctx: Context) -> str:
        last_label = list(ctx.labels)[-2] if len(ctx.labels) >= 2 else None
        return ctx.labels[last_label][1] if last_label is not None else "start_node"

    def ping_pong_response(ctx: Context, _: Pipeline, *args, **kwargs) -> Message:
        if get_previous_node_name(ctx) == "start_node":
            return Message(text="Hi! Let's play ping-pong!")
        else:
            return Message(text="Pong!")

    def fallback_response(ctx: Context, _: Pipeline, *args, **kwargs) -> Message:
        if ctx.last_request is not None:
            last_request = ctx.last_request.text
            note = f"You should've written 'Ping', not '{last_request}'!"
        else:
            note = "You should've just written 'Ping'!"
        if get_previous_node_name(ctx) == "start_node":
            return Message(text="You should've started the dialog with 'Hello!',"
                "anyway, let's play ping-pong!")
        else:
            return Message(text=f"That was against the rules! {note}")

    ping_pong_script = {
        "ping_pong_flow": {
            "start_node": {
                RESPONSE: Message(),
                TRANSITIONS: {
                    lbl.forward(): cnd.exact_match(Message(text="Hello!")),
                },
            },
            "ping_pong_node": {
                RESPONSE: ping_pong_response,
                TRANSITIONS: {
                    lbl.repeat(): cnd.regexp(r"^[P|p]ing!?$"),
                },
            },
            "fallback_node": {
                RESPONSE: fallback_response,
                TRANSITIONS: {
                    lbl.backward(): cnd.regexp(r"^[P|p]ing!?$"),
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
        run_interactive_mode(pipeline)

That's what we changed:

* ``greeting_node`` and ``response_node`` were merged, the resulting ``ping_pong_node`` has a
  callback response, it proposes user to play ping-pong if the previous node was ``start_node`` and
  plays ping-pong otherwise.

* ``fallback_node`` has a callback response as well, it prints different mesasages according to the
  previous node, that messages can also include user inputs.

.. note::

    See :doc:`tutorial on response functions <https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.3_responses.html>`.

* A special function ``get_previous_node_name`` was written to determine the value of the previous
  visited node. It utilizes ``labels`` attribute of ``Context`` object.

.. note::

    See :doc:`documentation of Context object <https://deeppavlov.github.io/dialog_flow_framework/apiref/dff.script.core.context.html>`.

* Transitions were changed: transitions to next, previous and current node were replaced with special
  standard transitions.

.. note::

    See :doc:`tutorial on transitions <https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.4_transitions.html>`.

* Conditions were changed: now regular expressions are used to check user text input value.

.. note::

    See :doc:`tutorial on conditions <https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.2_conditions.html>`.

Further exploration
~~~~~~~~~~~~~~~~~~~

There are still come capabilities of Dialog Flow Framework that remain uncovered by this tutorial.
For example:

* You can use ``GLOBAL`` transitions that will be available from every node in your script.
  See :doc:`tutorial on global transitions <https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.5_global_transitions.html>`.

* You can serialize context (available on every transition and response)
  to json or dictionary in order to debug it or extract some values.
  See :doc:`tutorial on context serialization <https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.6_context_serialization.html>`.

* You can alter user input and modify generated responses.
  User input can be altered with ``PRE_RESPONSE_PROCESSING`` and will happen **before** response generation.
  See :doc:`tutorial on pre-response processing <https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.7_pre_response_processing.html>`.
  Node response can be modified with ``PRE_TRANSITION_PROCESSING`` and will happen **after** response generation.
  See :doc:`tutorial on pre-transition processing <https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.9_pre_transitions_processing.html>`.

* Additional data ``MISC`` can be added to every node, flow and script itself.
  The values in MISC will be available during one script execution only; they will be cleared on each new user input.
  See :doc:`tutorial on script MISC <https://deeppavlov.github.io/dialog_flow_framework/tutorials/tutorials.script.core.8_misc.html>`.

Conclusion
~~~~~~~~~~

In this tutorial, we explored the basics of Dialog Flow Framework (DFF) to build dynamic conversational services.
By using DFF's intuitive Domain-Specific Language (DSL) and well-structured dialog graphs, we created a simple interaction between user and AI.
We covered installation, understanding the DSL and building dialog graph.
However, this is just the beginning. DFF offers a world of possibilities in conversational AI.
With practice and exploration of advanced features, you can create human-like conversations and reach a wider audience by integrating with various platforms.
Now, go forth, unleash your creativity, and create captivating conversational services with DFF.
Happy building!
