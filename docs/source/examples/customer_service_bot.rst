Customer service bot
--------------------

Customer service bot built using `DFF`. 
This bot is designed to answer any type of user questions in a limited business domain (book shop).
Uses a Telegram interface.

Project structure
~~~~~~~~~~~~~~~~~

While DFF allows you to choose any structure for your own projects,
we propose a schema of how project files can be meaningfully split
into services and modules.

* In our projects, we go for docker-based deployment due to its scalability and universal
    applicability. If you decide to go for the same deployment scheme, you will always
    have at least one service that wraps your bot.

* Neural network models that you run locally can be factored out into a separate service.
    This way your main service, i.e. the service wrapping the bot, won't crash if something
    unexpected happens with the model.

* In the main service directory, we make a separate package for all DFF-related abstractions.
    There, we put the script into a separate module, also creating modules for
    `processing, condition, and response functions <#>`__.

* The rest of the project-related Python code is factored out into other packages.

* We also create 'run.py' and 'test.py' at the project root. These files import the ready pipeline
    and execute it to test or run the service.

.. code-block:: shell

    examples/customer_service_bot/
    ├── docker-compose.yml # docker-compose orchestrates the services
    ├── bot # main docker service
    │   ├── api
    │   │   ├── __init__.py
    │   │   ├── chatgpt.py
    │   │   └── intent_catcher.py
    │   ├── dialog_graph # Separate package for DFF-related abstractions
    │   │   ├── __init__.py
    │   │   ├── conditions.py # Condition callbacks
    │   │   ├── consts.py # Constant values for keys
    │   │   ├── processing.py # Processing callbacks
    │   │   ├── response.py # Response callbacks
    │   │   └── script.py # DFF script and pipeline are constructed here
    │   ├── dockerfile # The dockerfile takes care of setting up the project. See the file for more details
    │   ├── requirements.txt
    │   ├── run.py
    │   └── test.py
    └── intent_catcher # intent catching model wrapped as a docker service
        ├── dockerfile
        ├── requirements.txt
        ├── server.py
        └── test_server.py