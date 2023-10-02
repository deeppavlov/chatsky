Optimization Guide
------------------

Introduction
~~~~~~~~~~~~

When optimizing a dialog service to provide the best possible user experience,
it's essential to identify and address performance issues.
Similar to any complex system, a dialog service can have performance bottlenecks at various levels.
These bottlenecks can occur during I/O operations like receiving and sending messages,
as well as when synchronizing service states with a database.
Even the efficiency of DFF classes can degrade
as the number of callbacks in the script and pipeline increases.

As a result, it becomes necessary to locate the part of the pipeline that is causing issues, so that
further optimization steps can be taken. DFF provides several tools that address the need for
profiling individual system components. This guide will walk you through the process
of using these tools in practice and optimizing the profiled application.

Profiling with Locust testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

[Locust](https://locust.io/) is a tool for load testing web applications that
simultaneously spawns several user agents that execute a pre-determined behavior
against the target application. Assuming that your pipeline is integrated into a web
server application, like Flask or FastAPI, that is not strongly impacted by the load,
the load testing reveals how well your pipeline would scale to a highly loaded environment.
Using this approach, you can also measure the scalability of each component in your pipeline,
if you take advantage of the Opentelemetry package bundled with the library (`stats` extra required)
as described below.

Since Locust testing can only target web apps, you will need to integrate your dialog pipeline into a web application.
At this stage, you will also need to instrument the pipeline components that you want to additionally profile
using `extractor functions`. Put simply, you are decorating the components of the pipeline
with functions that can report their performance, e.g. their execution time or the CPU load.

.. note::

    You can get more info on how instrumentation is done and statistics are collected
    in the `stats tutorial <../tutorials/tutorials.stats.1_extractor_functions.py>`_.

When you are done setting up the instrumentation, you can launch the web server to accept connections from locust.

The final step is to run a Locust file which will result in artificial load traffic being generated and sent to your server.
A Locust file is a script that implements the behavior of artificial users,
i.e. the requests to the server that will be made during testing.

.. note::

    An example Locust script along with instructions on how to run it can be found in the
    `load testing tutorial <../tutorials/tutorials.messengers.web_api_inference.3_load_testing_with_locust.py>`_.
    The simplest way, however, is to pass a locust file to the Python interpreter.

Once Locust is running, you can access its GUI, where you can set the number of users to emulate.
After configuring this parameter, the active phase of testing will begin,
and the results will become accessible on an interactive dashboard.
These reported values include timing data, such as the average response time of your service,
allowing you to assess the performance's reasonableness and impact on user experience.

The data provided by extractor functions will be available in the Clickhouse database;
you can view it using the Superset dashboard (see `instructions <./superset_guide.html>`_)
or analyze it with your own queries using the Clickhouse client.

Profiling context storages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Benchmarking the performance of context storage is crucial to understanding
how different storage methods impact your dialog service's efficiency.
This process involves running tests to measure the speed and reliability of various context storage solutions.
Given the exact configuration of your system, one or the other database type may be performing more efficiently,
so you may prefer to change your database depending on the testing results.
In the following sections, we will guide you through setting up and running context storage benchmarks.

**Context Storage Setup**

Before you can begin benchmarking, you need to set up the context storage options you want to test,
the available options including
* JSON: Uses JSON files for storage.
* Pickle: Utilizes Python's Pickle format for storage.
* Shelve: Utilizes Python's Shelve format for storage.
* PostgreSQL: A PostgreSQL database for storage.
* MongoDB: A MongoDB database for storage.
* Redis: A Redis database for storage.
* MySQL: A MySQL database for storage.
* SQLite: An SQLite database for storage.
* YDB: Utilizes YDB (Yandex Database) for storage.

For some storage methods like Pickle, Shelve, and SQLite, you may need to create temporary directories or files
to perform the benchmarking.

**Saving Benchmark Results to a File**

Benchmark results are saved to files for analysis and comparison.
There are two functions available for this purpose:

* benchmark_all: This function is a higher-level wrapper that accepts benchmark cases and configurations for multiple databases in a single file.
* save_results_to_file: This function accepts a single URI for the database and multiple benchmark configurations.

Both functions use a `BenchmarkConfig` to configure benchmark behavior.
The `BenchmarkConfig` allows you to set parameters
like the number of contexts that will be saved and retrieved from the storage during testing (context_num)
and the dimensions of messages and other components,
allowing for fine-grained control over the benchmarks.

**File Structure**

Benchmark results are saved according to a specific schema,
which can be found in the benchmark schema documentation.
Each database being benchmarked will have its own result file.

**Viewing Benchmark Results**

Once the benchmark results are saved to a file, you can view and analyze them using two methods:

* Using the Report Function: The report function can display specified information from a given file. By default, it prints the name and average metrics for each benchmark case.
* Using the Streamlit App: A Streamlit app is available for viewing and comparing benchmark results. You can upload benchmark result files using the app's "Benchmark sets" tab, inspect individual results in the "View" tab, and compare metrics in the "Compare" tab.

**Additional Information**

DFF provides configuration presets in the `basic config <../apiref/dff.utils.db_benchmarks.basic_config.py>`_ module,
covering various contexts, messages, and edge cases.
You can use these presets by passing them to the benchmark functions.

If the basic configurations are not sufficient for your needs, you can create custom configurations by inheriting from the BenchmarkConfig class.
You'll need to define three methods:

* `get_context` for getting initial contexts,
* `info` for getting display information representing the configuration,
* and `context_updater` for updating contexts.

.. note::

    The exact instructions of how the testing can be carried out are available in the
    `DB benchmarking tutorial <../tutorials/tutorials.context_storages.8_db_benchmarking.py>`_.

Optimization techniques
~~~~~~~~~~~~~~~~~~~~~~~

Aside from choosing an appropriate database type, there exists a number of other recommendations
that may help you improve the efficiency of your service.

* Firstly, follow the DRY principle not only with regard to your code, but also with regard to
  computational operations. In other words, you have to make sure that your callback functions work only once
  during a dialog turn and only when needed. E.g. you can take note of the `conditions` api available as a part
  of the `Pipeline` module: while normally a pipeline service runs every turn, you can restrict it
  to only run on turns when a particular condition is satisfied, greatly reducing
  the number of performed actions `<../tutorials/tutorials.pipeline.4_groups_and_conditions_full.py>`_.

* Using caching for resource-consuming callbacks and actions may also prove to be a helpful strategy.
  In this manner, you can improve the computational efficiency of your pipeline,
  while making very few changes to the code itself. DFF includes a caching mechanism
  for response functions: `<../tutorials/tutorials.utils.1_cache.py>`_. However, the simplicity
  of the DFF API makes it easy to integrate any custom caching solutions that you may come up with.

* Finally, be mindful about the use of computationally expensive algorithms, like NLU classifiers
  or LLM-based generative networks, since those require a great deal of time and resources
  to produce an answer. In case you need to use one, take full advantage of caching along with
  other means to relieve the computational load imposed by neural networks.
