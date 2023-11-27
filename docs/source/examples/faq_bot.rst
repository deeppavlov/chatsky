FAQ Bot
-------

FAQ bot for Arch Linux users built using `DFF`.
Can be run with Telegram or with a web interface.

You can read more about deploying the project in its README file.

Project structure
~~~~~~~~~~~~~~~~~

* In our projects, we go for docker-based deployment due to its scalability and universal
    applicability. If you decide to go for the same deployment scheme, you will always
    have at least one service that wraps your bot.

* In the main service directory, we make a separate package for all DFF-related abstractions.
    There, we put the `script <#>`__ into a separate module, also creating modules for
    `condition and response functions <#>`__.

* We also create a separate package for `pipeline services <#>`__.

* The rest of the project-related Python code is factored out into other packages.

* We also create 'run.py' and 'test.py' at the project root. These files import the ready pipeline
    and execute it to test or run the service.

.. code-block:: shell

    examples/frequently_asked_question_bot/telegram/
    ├── docker-compose.yml # docker-compose orchestrates the services
    └── bot # main docker service
        ├── Dockerfile # The dockerfile takes care of setting up the project. View the dockerfile for more detail
        ├── dialog_graph # Separate module for DFF-related abstractions
        │   ├── __init__.py
        │   ├── conditions.py # Condition callbacks
        │   ├── responses.py # Response callbacks
        │   └── script.py # DFF script and pipeline are constructed here
        ├── faq_model
        │   ├── __init__.py
        │   ├── faq_dataset_sample.json
        │   └── model.py
        ├── pipeline_services
        │   ├── __init__.py
        │   └── pre_services.py
        ├── requirements.txt
        ├── run.py # the web app imports the DFF pipeline from dialog_graph
        └── test.py # End-to-end testing happy path is defined here
    
Models
~~~~~~~

The project makes use of the `clips/mfaq <https://huggingface.co/clips/mfaq>`__ model that powers the bot's ability to understand queries in multiple languages.
A number of techniques is employed to make the usage more efficient.

* The project's Dockerfile illustrates caching a model using SentenceTransformer in a Docker container.
    The model is constructed during image build, so that the weights that the Huggingface library fetches from the web are downloaded in advance. At runtime, the fetched weights will be quickly read from the disk.
