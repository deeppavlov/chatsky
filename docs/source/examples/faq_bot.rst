FAQ Bot
-------

FAQ bot for Arch Linux users built using `DFF`.
Can be run with Telegram or with a web interface.

.. code-block:: shell

    project/
    ├── myapp
    │   ├── dialog_graph
    │   │   ├── __init__.py
    │   │   ├── conditions.py # Condition callbacks
    │   │   ├── processing.py # Processing callbacks
    │   │   ├── response.py # Response callbacks
    │   │   └── script.py # DFF script and pipeline are constructed here
    │   ├── dockerfile
    │   ├── requirements.txt
    │   ├── web_app.py # the web app imports the DFF pipeline from dialog_graph
    │   └── test.py # End-to-end testing happy path is defined here
    ├── ...Folders for other docker-based services, if applicable
    ├── venv/
    └── docker-compose.yml