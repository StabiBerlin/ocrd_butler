================================
ocrd_butler - Kitodo integration
================================

Here is an example of api calls for creating a new task for OCR recognition and download the results. The order describes a possible integration in a Kitodo workflow. The PPNs and UIDs are just placeholder.


Create a new task:

.. code-block:: bash

    ╰─$ curl -X POST -H 'Content-Type: application/json' http://ocrd-butler.sbb.berlin/api/tasks -d '{
            "description": "Test",
            "src": "https://content.staatsbibliothek-berlin.de/dc/PPN743946618.mets.xml",
            "default_file_grp": "MAX",
            "workflow_id": 1
        }'
        {"id":14,"message":"Task created.","uid":"eb121dad-7041-49af-9782-8d24cce5df66"}


Run the task:

.. code-block:: bash

    ╰─$ curl -X POST http://ocrd-butler.sbb.berlin/api/tasks/eb121dad-7041-49af-9782-8d24cce5df66/run
    {"status":"PENDING","traceback":null,"worker_task_id":"3b92b308-7421-4f9c-b0b3-323a35c2e5ae"}


Get status of the task:

.. code-block:: bash

    ╰─$ curl -X GET http://ocrd-butler.sbb.berlin/api/tasks/eb121dad-7041-49af-9782-8d24cce5df66/status
    {"status":"STARTED"}

    ╰─$ sleep 5000

    ╰─$ curl -X GET http://ocrd-butler.sbb.berlin/api/tasks/eb121dad-7041-49af-9782-8d24cce5df66/status
    {"status":"SUCCESS"}


If status is "SUCCESS"

.. code-block:: bash

    ╰─$ curl -X GET http://ocrd-butler.sbb.berlin/api/tasks/eb121dad-7041-49af-9782-8d24cce5df66/download_alto --output PPN743946618-alto.zip


Handle the ALTO files. Currently the conversion from PAGE to ALTO is not packed in an OCRD processor. Therefor we have no information in the METS file that can be used.
