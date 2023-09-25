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

...

Context storage benchmarking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

...