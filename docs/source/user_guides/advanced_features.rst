Best practices guide
-----------------------

Setting up a Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A virtual environment provides a controlled and isolated setup for your bot, minimizing conflicts
and ensuring consistency across different setups.

- If you already have a virtual environment and just need DFF as a component, install DFF using pip. If you need specific dependencies, install them using pip as well.
- If you prefer, you can clone the DFF GitHub repository and set up a virtual environment using the `make venv` command. This virtual environment will have all the necessary requirements for working with DFF.

Script Design
~~~~~~~~~~~~~

The foundation of your bot's ability to engage in meaningful conversation lies in its script.
In DFF, this process is structured around dividing your script into distinct flows.
A flow represents a self-contained piece of dialogue encompassing a particular topic or function.
More in the `basic guide <./basic_conceptions.rst>`__.

- Creating a Script: A script is a dictionary where keys correspond to different flows,
  which are used to divide a dialog into sub-dialogs and process them separately.

- Begin by brainstorming and listing down the primary functions and topics your bot needs to handle.

- For each function or topic, create a separate flow.
  Flows are dictionaries, with keys being nodes that represent the smallest unit of a dialog.
  Each flow should have a clear entry and exit point.

- Creating Nodes: A node contains the bot's response to a user's input,
  a condition determining the transition to another node,
  whether within the current or another flow.

- Ensure that there's a logical progression within each flow, guiding the user from the beginning to the end of the conversation segment.

Models
~~~~~~

Models are central to making your bot intelligent and responsive.
In the context of DFF, models may help in processing data and generating non-hardcoded responses.

- Set up caching mechanisms to improve response times by reducing the need for recalculations.
  You can straightforwardly cache the output of functions that leverage calls to NLU models
  or use more complex solutions, like `GPTcache <https://github.com/zilliztech/gptcache>`_

- The `Dockerfile <https://raw.githubusercontent.com/deeppavlov/dialog_flow_demo/main/frequently_asked_question_bot/telegram/bot/Dockerfile>`_ in the DFF demo
  illustrates caching a model using SentenceTransformer in a Docker container.
  The model is constructed during image build, so that the weights that the Huggingface library
  fetches from the web are downloaded in advance. At runtime, the fetched weights will be quickly read from the disk.

- Use persistent context storages to hold the necessary information that your bot will need.

Using Docker
~~~~~~~~~~~~

Docker simplifies the deployment of your bot by encapsulating it into containers.
The `docker-compose` file in the DFF repository provides a solid base for setting up your bot's environment.

- Make sure that Docker and Docker Compose are installed on your machine.

- Clone the GitHub-based distribution of DFF which includes a `docker-compose.yml <https://raw.githubusercontent.com/deeppavlov/dialog_flow_framework/master/docker-compose.yml>`_ file.

- The `docker-compose.yml <https://raw.githubusercontent.com/deeppavlov/dialog_flow_framework/master/docker-compose.yml>`_ file
  demonstrates the setup of various database services like MySQL, PostgreSQL, Redis, MongoDB, and others using Docker Compose.
  The file also showcases setting up other services and defines the network and volumes for data persistence.
  Customize the provided file to match your bot's requirements, such as specifying dependencies and environment variables.

- As a rule of thumb, most of the time you will need at least two docker containers: 1) The bot itself, containerized as a web application;
  2) Container for a database image. You can add the web app image to the docker-compose file and, optionally, add both containers
  to a single docker profile. 
  
.. code-block::

  web:
    build:
      context: web/
    volumes:
      - ./web/:/app:ro
    ports:
      - 8000:8000
    env_file:
      - ./.env
    depends_on:
      - psql
    profiles:
      - 'myapp'
  psql:
    # ... other options
    profiles:
      - 'myapp'

- This allows you to control both containers with a single docker command.
  
.. code-block::

  docker-compose --profile myapp up


- Use Docker Compose commands to build and run your bot.

Directory Structure
~~~~~~~~~~~~~~~~~~~

A well-organized directory structure is crucial for managing your bot's code, assets, and other resources effectively. The demo provided in the DFF repository serves as a good template.

- Organize your scripts, models, and other resources in a logical, hierarchical manner.

- Maintain a clean and well-documented codebase to facilitate maintenance and collaboration.

- You can create a directory for your bot project following the structure outlined
  in the `demo project <https://github.com/deeppavlov/dialog_flow_demo/tree/main/customer_service_bot>`_.

Testing and Load Testing
~~~~~~~~~~~~~~~~~~~~~~~~

Testing ensures that your bot functions as expected under various conditions, while load testing gauges its performance under high traffic.

- Regular bot functionality can be covered by simple end-to-end tests that include user requests and bot replies.
  Tests of this kind can be automated using the Pytest framework.
  The demo project includes an `example <https://github.com/deeppavlov/dialog_flow_demo/blob/main/frequently_asked_question_bot/telegram/bot/test.py>`_ of such a testing suite.

- Optimize your bot's performance by identifying bottlenecks during I/O operations and other levels.
  Utilize tools like Locust for load testing to ensure your bot scales well under high load conditions.
  Additionally, profile and benchmark different context storages to choose the most efficient one for your dialog service.

.. note::

    More in the `profiling user guide <#>`_.

- Profiling with Locust: DFF recommends using Locust for load testing to measure the scalability of each component in your pipeline,
  especially when integrated into a web server application like Flask or FastAPI.

- Profiling Context Storages: Benchmarking the performance of database bindings is crucial.
  DFF provides tools for measuring the speed and reliability of various context storage solutions like JSON,
  Pickle, PostgreSQL, MongoDB, Redis, MySQL, SQLite, and YDB.

Make use of telemetry
~~~~~~~~~~~~~~~~~~~~~

Another great way to measure the efficiency of your bot is to employ the telemetry mechanisms
that come packaged with DFF's GitHub distribution. Telemetry data can then be viewed
and played with by means of the integrated Superset dashboard.

.. note::

  For more information on working with Telemetry data, you can consult
  the `Stats Tutorial <../tutorials/tutorials.stats.1_extractor_functions.py>`_ 
  and the `Superset Guide <./superset_guide.rst>`__.

Choosing a Database
~~~~~~~~~~~~~~~~~~~

The choice of database technology affects your bot's performance and ease of data management.

- Evaluate the data requirements of your bot as well as the capabilities of your hardware
  (server or local machine) to determine the most suitable database technology.

- Set up and configure the database, ensuring it meets your bot’s data storage, retrieval, and processing needs.

- DFF supports various databases like JSON, Pickle, SQLite, PostgreSQL, MySQL, MongoDB, Redis, and Yandex Database.
