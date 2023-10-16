Slot Extraction
---------------

Introduction
~~~~~~~~~~~~

Extracting and filling slots is an essential part of any conversational service
that comprises the inherent business logic. Like most frameworks, DFF
provides components that address this task as a part of its `slots` module.
These can be easily customized to leverage neural networks specifically designed
for slot extraction or any other logic you might want to integrate.

API overview
~~~~~~~~~~~~

The basic building block of the API is the
`BaseSlot class <../apiref/dff.script.slots.types.html#dff.script.slots.types.BaseSlot>`_
and its descendants that vary depending on the value extraction logic.
Each slot has a name by which it can be accessed and a method for extracting values.
Below, we demonstrate the most basic class that extracts values
from user utterances using a regular expression and the
`RegexpSlot class <../apiref/dff.script.slots.types.html#dff.script.slots.types.RegexpSlot>`_.

.. code-block:: python

    from dff.script.slots import RegexpSlot
    ...
    email_slot = RegexpSlot(name="email", regexp=r"[a-z@\.A-Z]+")

The slots can implement arbitrary logic including requests to external services.
For instance, Deeppavlov library includes a number of models that may be of use for slot
extraction task. In particular, we will demonstrate the use of the following
`NER model <https://docs.deeppavlov.ai/en/master/features/models/NER.html>`_
that was trained and validated on the conll_2003 dataset.

.. code-block:: shell

    docker pull deeppavlov/deeppavlov:latest
    docker run -d --name=ner \
        -e CONFIG=ner_conll2003_bert \
        -p 5000:5000 \
        -v ~/.deeppavlov:/root/deeppavlov \
        -v ~/.cache:/root/cache \
        deeppavlov/deeppavlov:latest

Now that you have a Deeppavlov docker image running on port 5000, you can take the following steps to take
full advantage of its predictions.

.. code-block:: python

    import requests
    from dff.script.slots import FunctionSlot
    ...
    # we assume that there is a 'NER' service running on port 5000 
    def extract_first_name(utterance: str) -> str:
        """Return the first entity of type B-PER (first name) found in the utterance."""
        ner_request = requests.post(
            "http://localhost:5000/model",
            json={"x": [utterance]}
        )
        ner_tuple = ner_request.json()
        if "B-PER" not in ner_tuple[1][0]:
            return ""
        return ner_tuple[0][0][ner_tuple[1][0].index("B-PER")]

    name_slot = FunctionSlot(name="first_name", func=extract_first_name)

Individual slots can be grouped allowing the developer to access them together
as a namespace. This can be achieved using the
`GroupSlot <../apiref/dff.script.slots.types.html#dff.script.slots.types.GroupSlot>`_
component that can be initialized with a list of other slot instances as its children.
The group slots also allow for arbitrary nesting, i.e. it is possible to include
group slots in other group slots.

.. code-block:: python

    from dff.script.slots import GroupSlot
    ...
    profile_slot = slots.GroupSlot(name="profile", children=[name_slot, email_slot])

When all slots have been defined, you can refer to them in your script.
Slots can be extracted at the `PRE_TRANSITIONS_PROCESSING` stage
using the `extract <../apiref/dff.script.slots.processing.html#dff.script.slots.processing.extract>`_
function from the ``processing`` submodule, which looks up a slot by name and uses
associated method to extract values.
The only argument is the list of names of the slots that you want to extract
from user utterances.

.. code-block:: python

    from dff.script.slots.processing import extract
    ...
    PRE_TRANSITIONS_PROCESSING: {"extract_first_name": extract(["first_name"])}

If you need to use slot values as conditions for dialog script traversal,
you can use functions from the `conditions` module.

.. code-block:: python
    
    from dff.script.slots.conditions import is_set_all, is_set_any
    ...
    TRANSITIONS: {"all_information": is_set_all(["first_name", "email"])}
    TRANSITIONS: {"partial_information": is_set_any(["first_name", "email"])}

The `processing` module also provides functions that fill templates
with slot values.

.. code-block:: python
    
    from dff.script.slots.processing import fill_template
    ...
    PRE_RESPONSE_PROCESSING: {"fill_response_slots": slot_procs.fill_template()}
    RESPONSE: Message(text="Your first name: {first_name}")

Some real examples of scripts that leverage slot extraction can be found in the
`tutorials section <../tutorials/tutorials.slots.1_basic_example.html>`_.

Form Policy
~~~~~~~~~~~

On some occasions, we need to collect some specific information from the user, like
the details of the purchase they want to make. In such cases, we want the chatbot
to ask questions, until it has all the necessary info.
Dialog Flow Framework provides the means to achieve that, namely a special
`policy component <../apiref/dff.script.slots.forms.html#dff.script.slots.forms.FormPolicy>`_
that can be integrated in your script.
This class checks on the state of a set of slots, and,
as long as any of them is still missing a value,
it enables transitions to the nodes that fill them.

.. code-block:: python
    :linenos:

    from dff.script.slots import FormPolicy
    ...
    # slot names are mapped to node addresses
    form_policy = slots.FormPolicy(
        "restaurant",
        {
            "restaurant_cuisine": [("restaurant", "cuisine")],
            "restaurant_address": [("restaurant", "address")],
            "restaurant_number": [("restaurant", "number")],
        },
    )

The form policy class includes several methods that need to be used in the script. Most importantly,
`to_next_label <../apiref/dff.script.slots.types.html#dff.script.slots.types.GroupSlot.to_next_label>`_
method needs to be used as a transition target.
This will lead to the policy suggesting one of the nodes in the mapping
given that the respective slot is not set.

.. code-block:: python

    form_policy.to_next_label(1.1): cnd.true(),

The form is also a stateful object which requires the user to leverage the methods
for state management. States should be updated at the `PRE_TRANSITIONS_PROCESSING` stage
which can be done at the `GLOBAL` level.

.. code-block:: python

    PRE_TRANSITIONS_PROCESSING: {"update_action": form_policy.update_state()}

Meanwhile, it is also possible to make transitions depending on state values
of a form policy.

.. code-block:: python

    TRANSITIONS: {("flow", "node"): form_policy.has_state(FormState.ACTIVE)}

An interactive example can be found in the
`form tutorial <../tutorials/tutorials.slots.2_form_example.html>`_.
