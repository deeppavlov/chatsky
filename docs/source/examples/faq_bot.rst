FAQ Bot
-------

FAQ bot for Deeppavlov users built using `DFF`.
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


.. code-block:: shell

    examples/frequently_asked_question_bot/
    ├── README.md
    ├── compose.yml # docker compose file orchestrates the services
    ├── nginx.conf # web service proxy configurations
    └── web
        ├── Dockerfile
        ├── app.py
        ├── bot
        │   ├── dialog_graph # A separate module for DFF-related abstractions
        │   │   ├── responses.py
        │   │   └── script.py # DFF script is constructed here
        │   ├── faq_model # model-related code
        │   │   ├── faq_dataset_sample.json
        │   │   ├── model.py
        │   │   ├── request_translations.json
        │   │   └── response_translations.json
        │   ├── pipeline.py
        │   ├── pipeline_services # Separately stored pipeline service functions
        │   │   └── pre_services.py
        │   └── test.py
        ├── requirements.txt
        └── static
            ├── LICENSE.txt
            ├── index.css
            ├── index.html
            └── index.js
    
Models
~~~~~~~

The project makes use of the `clips/mfaq <https://huggingface.co/clips/mfaq>`__ model that powers the bot's ability to understand queries in multiple languages.
A number of techniques is employed to make the usage more efficient.

* The project's Dockerfile illustrates caching a model using SentenceTransformer in a Docker container.
    The model is constructed during image build, so that the weights that the Huggingface library fetches from the web are downloaded in advance. At runtime, the fetched weights will be quickly read from the disk.
