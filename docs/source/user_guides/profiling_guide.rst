Profiling Guide
----------------

Profiling dialog services
-------------------------

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
of using these tools in practice.

Load testing with Locust
~~~~~~~~~~~~~~~~~~~~~~~~

[Locust](https://locust.io/) is a tool for load testing web applications that
simultaneously spawns several user agents that execute a pre-determined behavior
against the target application. Assuming that your pipeline is integrated into a web
server application, like Flask or FastAPI, that is not strongly impacted by the load,
the load testing reveals how well your pipeline scales to a highly loaded environment.

.. note::

    The exact instructions of how the testing can be carried out are available in the
    `load testing tutorial <../tutorials/tutorials.messengers.web_api_inference.3_load_testing_with_locust.py>`_.

In general, the process involves launching your web application and Locust simultaneously. Once Locust is running, you can access its GUI, where you can configure the number of users to simulate. After configuring this parameter, the testing begins, and the results are displayed on an interactive dashboard. These results include timing data, such as the average response time of your service, allowing you to assess the performance's reasonableness and impact on user experience.

Additionally, you can leverage the Opentelemetry package bundled with the stats extra. Configure logging for every component of your web app to measure execution times under high-load conditions. This approach helps reveal the source of performance issues, if any.

Context storage benchmarking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Benchmarking the performance of context storage is crucial to understanding
how different storage methods impact your dialog service's efficiency.
This process involves running tests to measure the speed and reliability of various context storage solutions.
In the following sections, we will guide you through setting up and running context storage benchmarks.

**Context Storage Setup**

Before you can begin benchmarking, you need to set up the context storage options you want to test.
The following storage methods are available for benchmarking:

    JSON: Uses JSON files for storage.
    Pickle: Utilizes Python's Pickle format for storage.
    Shelve: Utilizes Python's Shelve format for storage.
    PostgreSQL: A PostgreSQL database for storage.
    MongoDB: A MongoDB database for storage.
    Redis: A Redis database for storage.
    MySQL: A MySQL database for storage.
    SQLite: An SQLite database for storage.
    YDB: Utilizes YDB (Yandex Database) for storage.

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

DFF provides configuration presets in the dff.utils.db_benchmarks.basic_config module,
covering various contexts, messages, and edge cases.
You can use these presets by passing them to the benchmark functions.

If the basic configurations are not sufficient for your needs, you can create custom configurations by inheriting from the BenchmarkConfig class.
You'll need to define three methods:

* `get_context` for getting initial contexts,
* `info` for getting display information representing the configuration,
* and `context_updater` for updating contexts.

.. note::

    The exact instructions of how the testing can be carried out are available in the
    `load testing tutorial <../tutorials/tutorials.context_storages.8_db_benchmarking.py>`_.