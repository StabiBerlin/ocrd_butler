===========
ocrd_butler
===========


.. image:: https://img.shields.io/pypi/v/ocrd_butler.svg
        :target: https://pypi.python.org/pypi/ocrd_butler

.. image:: https://img.shields.io/travis/j23d/ocrd_butler.svg
        :target: https://travis-ci.org/j23d/ocrd_butler

.. image:: https://readthedocs.org/projects/ocrd-butler/badge/?version=latest
        :target: https://ocrd-butler.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/j23d/ocrd_butler/shield.svg
     :target: https://pyup.io/repos/github/j23d/ocrd_butler/
     :alt: Updates


Processing tasks in the ecosystem of the [OCR-D](https://github.com/OCR-D) project.

* Free software: Apache Software License 2.0
* Documentation: https://ocrd-butler.readthedocs.io.


Features
--------

REST API to run tasks for OCR-D.

Development installation
------------------------

We rely on the excellent installation repository `ocrd_all`_. Please check it out for installation.

If your in the need to install it on a Debian 10 system (as we are), consider the following:

*

Install in development mode:


#We need to install the master branch of pipenv to get manylinux2010 included to be able to lock the dependency #functool32 of ocrd_calamari.
#
#.. code-block:: bash
#
#    ╰─$ pip install --user git+https://github.com/pypa/pipenv.git@master
#
#.. code-block:: bash
#
#    ╰─$ pipenv install
#    ╰─$ python setup.py develop

Run the app:

.. code-block:: bash

    ╰─$ TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata FLASK_APP=ocrd_butler/app.py flask run
    ╰─$ FLASK_APP=ocrd_butler/app.py flask run


Start celery worker:

.. code-block:: bash

    ╰─$ TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata celery worker -A ocrd_butler.celery_worker.celery -E -l info
    ╰─$ celery worker -A ocrd_butler.celery_worker.celery -E -l info

If download of METS files fail - disable the proxy on local machines. There are, as always, problems with network connections due to the proxy.

Swagger docs: http://localhost:5000/api

Start flower monitor:

.. code-block:: bash

    ╰─$ flower --broker redis://localhost:6379

Flower monitor: http://localhost:5555

Run the tests:

.. code-block:: bash

    ╰─$ TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata py.test


Resources
---------
`Flask + Celery = how to. <https://medium.com/@frassetto.stefano/flask-celery-howto-d106958a15fe>`

Ideas
-----

- Persistent tasks via flower (db and persistent option not working?) or transfer to own db?
- Form frontend for tasks and chains.
- Start date / Excecution times of tasks
- input and output filegroups are not always from the previous processor
  - could be more complicated - maybe we get it from the ocrd-tools.json
- forms with json-schema (directly builded from ocrd_tools.json?
- dinglehopper:
  - If there are Ground Truth data it could be placed in a configured folder
    on the server with the data as page xml files inside a folder id named with the
    work id. Then we show a button to start a run against this data.
    Otherwise we can search for all other tasks with the same work_id and present
    a UI to run against the choosen one.
- maybe the PROCESSORS can be dynamically generated out of the ocrd_tools.json of the
  installed packages.
- switch to RabbitMQ instead of Redis as broker to be consistent with Kitodo?
- Use processor groups to be able to build forms with these presented.

TODOs
-----
- tasks have to updated with:
  - start and end times
  - tags
  - description / notes


Credits
-------

This package was created with Cookiecutter_ and the
`elgertam/cookiecutter-pipenv`_ project template,
based on `audreyr/cookiecutter-pypackage`_.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`elgertam/cookiecutter-pipenv`: https://github.com/elgertam/cookiecutter-pipenv
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`ocrd_all`: https://github.com/OCR-D/ocrd_all
