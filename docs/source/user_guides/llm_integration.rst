LLM Integration
---------------

Introduction
~~~~~~~~~~~~

Introduction of LLMs in your script can gradually extend functionality and versatility of your dialogue system.
It can help to bring more life into overall formal and rule-like conversation and also leverage understanding of users intentions and responsiveness.
Chatsky provides you with a simple yet versatile way of adding Large Language Models into your dialogue script for generating responses and checking conditions.

API overview
~~~~~~~~~~~~

Models
===============

Under the hood Chatsky uses LangChain classes for accessing different models APIs.
These models, defined in the langchain_* should be passed in the `LLM_API` object as a parameter.

.. code-block:: python

    from chatsky.llm.wrapper import LLM_API
    from chatsky.pipeline import Pipeline
    from langchain_openai import ChatOpenAI
    
    model = LLM_API(ChatOpenAI(model="gpt-3.5-turbo"), system_prompt="You are an experienced barista in a local coffeshop. Answer your customers questions about coffee and barista work.")


Another parameter is the `system_prompt` that defines system prompt that will be used for this particular model.
You can also define multiple models and use all of them throughout your script. All of them must be then defined in the "models" field of the Pipeline.

.. code-block:: python

    from chatsky.llm.wrapper import LLM_API
    from chatsky.pipeline import Pipeline
    from langchain_openai import ChatOpenAI
    
    model_1 = LLM_API(ChatOpenAI(model="gpt-3.5-turbo"), system_prompt="system prompt 1")
    model_2 = LLM_API(ChatOpenAI(model="gpt-4"), system_prompt="system prompt 2")

    pipeline = Pipeline.from_script(
        ...,
        models={"model_name_1": model_1, "model_name_2": model_2}
        )

Responses
=========

Chatsky provides you with a simple functions to use for receiving Message object containing models response.

.. code-block:: python
    
    from chatsky.llm.wrapper import LLM_API, llm_response
    ...
    RESPONSE: llm_response(model_name="model_name_1")

Although you can overwrite this function for more fine-grained usage.

Conditions
==========


History management
==================

Prompts
=======

Another useful feature is the definition of multiple prompts for the different flows and nodes of the script.