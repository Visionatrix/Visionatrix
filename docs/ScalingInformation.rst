Scaling Information
===================

Visionatrix(**Vix**) consists of:

1. Server part, that is, the backend
2. Simple and understandable UI
3. The part responsible for processing Tasks
4. TaskQueue - database (SQLite *(default)*, MySQL/MariaDB, PgSQL)

By default, Vix launches with everything together(Server + Worker + UI), for quick and easy use on one computer.

However, in most cases, even in home use, you have more than one device that can handle AI tasks and in this case,
several extended use cases are allowed and recommended.

Client to Database-FS
"""""""""""""""""""""

.. note:: Requirements:

    1. Database used by the **Server** should be accessible for client.
    2. Ability to map the **Server**'s ``task_files`` folder to the client.

TO-DO


Client to Server
""""""""""""""""

TO-DO
