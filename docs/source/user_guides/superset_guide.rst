:orphan:

Superset guide
---------------------

Description
~~~~~~~~~~~

| The Dialog Flow Stats module can be used to obtain and visualize usage statistics for your service.
| Data aggregation relies on the `OpenTelemetry protocol <#>`_ and the `OpenTelemetry collector <#>`_ along with `Clickhouse <https://clickhouse.com/>`_ as an OLAP storage.
| Interactive visualization is powered by `Apache Superset <https://superset.apache.org/>`_.
| All the mentioned services are shipped as Docker containers, including a pre-built Superset image that ensures API compatibility.
| Authorization credentials can be automatically configured through environment variables.

.. code-block:: shell

    echo 'SUPERSET_USERNAME=...' >> .env
    echo 'SUPERSET_PASSWORD=...' >> .env
    docker run --env-file='.env' ghcr.io/deeppavlov/superset_df_dashboard:latest

Collection procedure
~~~~~~~~~~~~~~~~~~~~

**Installation**

.. code-block:: shell

    pip install dff[stats,clickhouse]
    pip install dff[stats,postgresql]

**Launching services**

.. code-block:: shell

    docker-compose up

**Setting up a pipeline**

.. warning::
    It is essential that you use `get_current_label` at least once, so that the default Superset charts
    can be successfully displayed.

.. code-block:: python
    :linenos:

    # import dependencies
    from dff.pipeline import Pipeline, Service, ACTOR
    from dff.stats import default_extractors
    # using default_extractors.current_label is required for dashboard integration 
    from dff.stats import OtelInstrumentor, set_logger_destination, set_tracer_destination
    from dff.stats import OTLPLogExporter, OTLPSpanExporter
    # initialize opentelemetry
    # insecure parameter ensures that SSL encryption is not forced
    dff_instrumentor = OtelInstrumentor.from_url("grpc://localhost:4317", insecure=True)
    dff_instrumentor.instrument()
    # Special extractor functions can be used as handlers to report statistics for any pipeline component.
    pipeline = Pipeline.from_dict(
        {
            "components": [
                Service(
                    handler=ACTOR,
                    after_handler=[
                        default_extractors.get_current_label, # using required extractor
                    ],
                ),
            ]
        }
    )
    pipeline.run()

Displaying the data
~~~~~~~~~~~~~~~~~~~

In order to display the Superset dashboard, you should update the default configuration with the credentials of your database.
The configuration can be optionally saved as a zip archive for inspection / debug.

You can set most of the configuration options using a YAML file.

.. code-block:: yaml
    :linenos:

    # config.yaml
    db:
        type: clickhousedb+connect
        name: test
        user: user
        host: localhost
        port: 5432
        table: dff_stats

The file can then be used to parametrize the configuration script.
Password values can be omitted and set interactively.

.. code-block:: shell
    :linenos:

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
shipped with DFF, make sure that your access rights are sufficient to edit the workspace.

Using Superset
~~~~~~~~~~~~~~

| In order to view the imported dashboard, log into Superset using your username and password.
| The dashboard will then be available in the **Dashboards** section of the Superset UI under the name of **DFF stats**.
| The dashboard has four sections, each one of them containing different kind of data.

*  The **Overview** section summarizes the information about user interaction with your script. And displays a weighted graph of transitions from one node to another. The data is also shown in the form of a table for better introspection capabilities.

.. figure:: ../_static/images/overview.png

    Overview plots.

* The data displayed in the **General stats** section reports, how frequent each of the nodes in your script was visited by users. The information is aggregated in several forms for better interpretability.

.. figure:: ../_static/images/general_stats.png

    General stats plots.

* The **Additional stats** section includes charts for node visit counts aggregated over various specific variables.

.. figure:: ../_static/images/additional_stats.png

    Additional stats plots.

* General service load data aggregated over time can be found in the **Service stats** section.

.. figure:: ../_static/images/service_stats.png

    Service stats plots.

On some occasions, Superset can show warnings about the database connection being faulty.
In that case, you can navigate to the `Database Connections` section through the `Settings` menu and edit the `dff_database` instance updating the credentials.

.. figure:: ../_static/images/databases.png

    Locate the database settings in the right corner of the screen.