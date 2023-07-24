Superset configuration
=======================

Description
-----------

| Dialog Flow Stats collects usage statistics for your conversational service and allows you to visualize them using a pre-configured dashboard for [Apache Superset](https://superset.apache.org/) or [Preset](https://preset.io/).
| We provide a pre-built Superset Docker image that includes all the necessary dependencies and ensures API compatibility. 
| Authorization credentials for the image can be automatically configured via environment variables.

.. code-block:: shell
    echo 'SUPERSET_USERNAME=...' >> .env
    echo 'SUPERSET_PASSWORD=...' >> .env
    docker run --env-file='.env' ghcr.io/deeppavlov/superset_df_dashboard:latest

Currently, support is offered for multiple database types that can be used as a backend storage for your data:

* [Postgresql](https://www.postgresql.org/)
* [Clickhouse](https://clickhouse.com/)

In addition, you can use the library without any dependencies
to save your service logs to *csv*-formatted files.

Installation
------------

.. code-block:: shell
    pip install dff[stats] # csv-only, no connection to Superset
    pip install dff[stats,clickhouse]
    pip install dff[stats,postgresql]

**Setting up a pipeline**

.. code-block:: python
    # import dependencies
    from dff.pipeline import Pipeline, Service, ACTOR
    from dff.stats import default_extractors
    from dff.stats import OtelInstrumentor, set_logger_destination, set_tracer_destination
    from dff.stats import OTLPLogExporter, OTLPSpanExporter
    # initialize opentelemetry
    # insecure parameter allows for SSL-independent connections
    set_logger_destination(OTLPLogExporter("grpc://localhost:4317", insecure=True))
    set_tracer_destination(OTLPSpanExporter("grpc://localhost:4317", insecure=True))
    dff_instrumentor = OtelInstrumentor()
    dff_instrumentor.instrument()
    # Instrumentation is applied to pipeline's extra handlers so that their output
    # gets persisted to the database. Use these handlers to report statistics
    # about a particular service in the pipeline.
    pipeline = Pipeline.from_dict(
        {
            "components": [
                Service(
                    handler=ACTOR,
                    before_handler=[default_extractors.get_timing_before],
                    after_handler=[
                        default_extractors.get_timing_after,
                        default_extractors.get_current_label,
                    ],
                ),
            ]
        }
    )
    pipeline.run()

Displaying the data
-------------------

In order to run the dashboard in Apache Superset, you should update the default configuration with the credentials of your database.
The configuration can be optionally persisted as a zip archive.

You can set the majority of the configuration options using a YAML file. 

.. code-block:: yaml
    # config.yaml
    db:
        type: clickhousedb+connect
        name: test
        user: user
        host: localhost
        port: 5432
        table: dff_stats

The file should then be forwarded to the configuration script:

.. code-block:: shell
    dff.stats config.yaml \
    -U superset_user \
    -P superset_password \
    -dP database_password \
    --db.type=postgresql \
    --db.user=root \
    --db.host=localhost \
    --db.port=5432 \
    --db.name=test \
    --db.table=dff_stats \
    --outfile=config_artifact.zip

Running the command will automatically import the dashboard as well as the data sources
into the running superset server. If you are using a version of Superset different from the one
shipped with DFF, make sure that your access rights are sufficient to update and edit
dashboards and data sources.

Navigating Superset
-------------------