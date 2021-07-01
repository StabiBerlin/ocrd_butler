===========
ocrd_butler
===========

.. .. image:: https://img.shields.io/travis/StaatsbibliothekBerlin/ocrd_butler.svg
..         :target: https://travis-ci.org/StaatsbibliothekBerlin/ocrd_butler


Processing tasks in the ecosystem of the `OCR-D project`_ project.


Features
--------

REST API to define chains of processors and run tasks with it in the OCR-D ecosystem.


Hints
-----

* Free software: MIT License

* This software is in alpha state yet, so don't expect it to work properly. Support is currently not guarenteed.


Development installation
------------------------

We rely on the excellent installation repository `ocrd_all`_.
Please check it out for installation.

Installation is currently tested on Debian 10 and Ubuntu 18.04.
Be aware that on more up-to-date systems with Python >= 3.8.x there is currently a problem installing tensorflow==1.15.x, so you have to use at most Python 3.7.

Installation for development:

Install Redis Server (needed as backend for Celery and Flower)

.. code-block:: bash

  user@server:/ > sudo apt install redis
  user@server:/ > sudo service redis start

Follow the installation for `ocrd_all`_

.. code-block:: bash

  /home/ocrd > git clone --recurse-submodules https://github.com/OCR-D/ocrd_all.git && cd ocrd_all
  /home/ocrd/ocrd_all > make all
  ... -> download appropriate modules...

Install german language files for Tesseract OCR:

.. code-block:: bash

  user@server:/ > sudo apt install tesseract-ocr-deu

Install ocrd-butler in the virtual environment created by ocrd_all:

.. code-block:: bash

  /home/ocrd > git clone https://github.com/StaatsbibliothekBerlin/ocrd_butler.git & cd ocrd-butler
  /home/ocrd/ocrd-butler > source ../ocrd_all/venv/bin/activate
  (venv) /home/ocrd/ocrd-butler > pip install -r requirements.txt
  (venv) /home/ocrd/ocrd-butler > pip install -r requirements-dev.txt
  (venv) /home/ocrd/ocrd-butler > python setup.py develop


For some modules in `ocrd_all`_ there are further files nessesary, e.g. trained models for the OCR itself. The folders on the server can be overwritten it every single task.

* ``sbb_textline_detector`` (i.e. ``make textline-detector-model``):

.. code-block:: bash

  > mkdir -p /data && cd /data; \
  > ocrd resmgr download ocrd-sbb-textline-detector default -al cwd


* ``ocrd_calamari`` (i.e. ``make calamari-model``):

.. code-block:: bash

  > mkdir -p /data && cd /data; \
  > ocrd resmgr download ocrd-calamari-recognize qurator-gt4histocr-1.0 -al cwd


* ``ocrd_tesserocr`` (i.e. ``make tesseract-model``):

.. code-block:: bash

  > mkdir -p /data/tesseract_models && cd /data/tesseract_models
  > wget https://qurator-data.de/tesseract-models/GT4HistOCR/models.tar
  > tar xf models.tar
  > cp GT4HistOCR_2000000.traineddata /usr/share/tesseract-ocr/4.00/tessdata/


* ``ocrd-sbb-binarize`` (i.e. ``make sbb-binarize-model``)

.. code-block:: bash

  > mkdir -p /data && cd /data; \
  > ocrd resmgr download ocrd-sbb-binarize default -al cwd


Start celery worker:

.. code-block:: bash

    ╰─$ TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata celery worker -A ocrd_butler.celery_worker.celery -E -l info

Start flower monitor:

.. code-block:: bash

    ╰─$ flower --broker redis://localhost:6379 --persistent=True --db=flower [--log=debug --url_prefix=flower]

Flower monitor: http://localhost:5555


Run the app:

.. code-block:: bash

    ╰─$ FLASK_APP=ocrd_butler/app.py flask run


Flask frontend: http://localhost:5000
Swagger interface: http://localhost:5000/api


Run the tests:

.. code-block:: bash

    ╰─$ make test


Known problems
--------------

ModuleNotFoundError: No module named 'tensorflow.contrib'

.. code-block:: bash

    . venv/activate
    pip install --upgrade pip
    pip uninstall tensorflow
    pip install tensorflow-gpu==1.15.*


TODOs
-----

- input and output filegroups are not always from the previous processor
  - more complicated input/output group scenarios
  - check the infos we get from ocrd-tools.json
- dinglehopper:
  - If there are Ground Truth data it could be placed in a configured folder on the server with the data as page xml files inside a folder id named with the work id. Then we show a button to start a run against this data.
  Otherwise we can search for all other tasks with the same work_id and present a UI to run against the choosen one.
- Use processor groups to be able to build forms with these presented.
- Check if ocrd-olena-binarize fail with another name for a METS file in a
  workspace then mets.xml.
- Refactor ocrd_tool information collection to https://ocr-d.de/en/spec/cli#-j---dump-json

This package was created with Cookiecutter_ and the `elgertam/cookiecutter-pipenv`_ project template, based on `audreyr/cookiecutter-pypackage`_.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`elgertam/cookiecutter-pipenv`: https://github.com/elgertam/cookiecutter-pipenv
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`ocrd_all`: https://github.com/OCR-D/ocrd_all
.. _`OCR-D project`: https://github.com/OCR-D
.. _`Qurator Data`: https://qurator-data.de/
.. _`OCR-D ecosystem`: https://github.com/topics/ocr-d
.. _tesseract-ocr-deu debian: https://packages.debian.org/de/sid/tesseract-ocr-deu