Profiling Guide
----------------

Profiling dialog services
-------------------------

Introduction
~~~~~~~~~~~~

When facing the task of delivering optimal experience to the users, it's crucial to identify and
resolve performance issues. Like any complex system, a dialog service has many levels on which performance bottlenecks can appear.
For instance, the I/O process of receiving messages or replying back to the user can become performance-hurting;
and so can the process of synchronizing service states with a database. Finally, as more callbacks are added
to the script and the pipeline, even the DFF classes can start to lack performance.

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

The exact instructions of how the testing can be carried out are available in the
`load testing tutorial <../tutorials/tutorials.messengers.web_api_inference.3_load_testing_with_locust.py>`_.
In general, it requires you to simultaneously launch the web tested application
and Locust. When Locust has been launched, you can visit the Locust GUI that will prompt you
for the number of users to spawn. After this parameter is configured, the testing will begin,
with the results displayed on an interactive dashboard.
The reported data includes timing parameters, such as the average time that your service takes to respond;
thus, you would be able to tell whether the timing is reasonable and does not hinder the user experience.

Additionally, you can take advantage of the Opentelemetry package that comes
bundled with the `stats` extra and configure logging for every component
of your web app. This will allow you to measure the execution time of each component
in high-load conditions revealing the source of performance issues, if any.

Context storage benchmarking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

...