Scaling Information
===================

Visionatrix(**Vix**) consists of:

1. A server component, namely, the backend `(in short - Server)`
2. A component responsible for processing tasks `(in short - Worker)`
3. TaskQueue - a database (SQLite *(default)*, MySQL/MariaDB, PgSQL)
4. A simple and understandable UI

By default, Vix launches with all components integrated (Server + Worker + UI) for quick and easy use on a single computer.

However, in most scenarios, including home use, you likely have more than one device capable of handling AI tasks.
In such cases, several extended use cases are permitted and recommended.

Each worker can have a different set of tasks (Flows) installed, which is useful to avoid installing a task on a worker instance that cannot handle it.
A worker will only request the tasks installed for it.

Worker to Database-FS
"""""""""""""""""""""

.. note:: Requirements:

    1. The database used by the **Server** should be accessible for the worker.
    2. There should be the ability to map the **Server**'s ``vix_tasks_files`` folder to the worker.

Set the environment variable ``VIX_MODE`` to **WORKER** and leave ``VIX_HOST`` with an empty value; do not set it.

In this scenario, the worker must be configured with the correct database path using the ``DATABASE_URI`` environment variable.
The format can be viewed here: `SqlAlchemy Database URLs <https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls>`_

By using the ``TASKS_FILES_DIR`` environment variable or the ``--tasks_files_dir`` argument, you can change the location of the  ``vix_tasks_files`` folder.
The worker must have access to the Server's ``vix_tasks_files`` folder.

With this scaling method, workers independently retrieve tasks from the database and directly write the execution results.

In this setup, you can imagine workers as Server threads operating remotely.

Worker to Server
""""""""""""""""

This method implies that the workers do not have direct access to the database or the server file system.

All communication occurs through the network, with workers accessing the server backend directly.

Set the environment variable ``VIX_MODE`` to **WORKER** and set ``VIX_HOST`` with the full address of the Server.

.. note:: ``VIX_PORT`` will be ignored, if a port is required, **VIX_HOST** should include it.

    ``DATABASE_URI`` will ignored in this scenario as well, as the worker does not need it.

In this use case, the **vix_tasks_files** directory will contain only temporary files; after uploading results to the Server, the results from the worker instance will be cleared.
