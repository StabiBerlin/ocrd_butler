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

Install in development mode:
.. code-block: bash
pipenv install
python setup.py develop

Run the app:
.. code-block: bash
FLASK_APP=ocrd_butler/app.py flask run
# TESSDATA_PREFIX=/usr/share/tessdata FLASK_APP=ocrd_butler/app.py flask run
# TESSDATA_PREFIX=/usr/share/tesseract-ocr/tessdata FLASK_APP=ocrd_butler/app.py flask run
# TESSDATA_PREFIX=/usr/local/share/tessdata FLASK_APP=ocrd_butler/app.py flask run


Start celery worker:
.. code-block: bash
TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata celery worker -A ocrd_butler.celery_worker.celery -E -l info
# TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata celery -A ocrd_butler.app.celery worker -E -l info
# TESSDATA_PREFIX=/usr/share/tessdata celery -A ocrd_butler.app.celery worker -E -l info

--> If download fails - disable the proxy on local machines. Problems with network connections are due to the proxy by default.

Swagger docs: http://localhost:5000

Start flower monitor:
.. code-block: bash
flower --broker redis://redis.localhost:6379

Flower monitor: http://localhost:5555

Resources
---------
[Flask + Celery = how to.](https://medium.com/@frassetto.stefano/flask-celery-howto-d106958a15fe)

Credits
-------

This package was created with Cookiecutter_ and the
`elgertam/cookiecutter-pipenv`_ project template,
based on `audreyr/cookiecutter-pypackage`_.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`elgertam/cookiecutter-pipenv`: https://github.com/elgertam/cookiecutter-pipenv
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
