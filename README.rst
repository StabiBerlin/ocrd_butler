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

* This software is in alpha state yet, so don't expect it to work properly. Support is currently not guaranteed.


Development installation
------------------------

We rely on the excellent installation repository `ocrd_all`_.
Please check it out for installation.

Installation is currently tested on Debian 10 and Ubuntu 18.04.
Be aware that on more up-to-date systems with Python >= 3.8.x there is currently a problem installing tensorflow==1.15.x, so you have to use at most Python 3.7.

Installation for development:

Follow the installation for `ocrd_all`_

.. code-block:: bash

  /home/ocrd > git clone https://github.com/OCR-D/ocrd_all.git & cd ocrd_all
  /home/ocrd/ocrd_all > make all
  ... -> download appropriate models...

Install ocrd-butler in the virtual environment created by ocrd_all:

.. code-block:: bash

  /home/ocrd > git clone https://github.com/StaatsbibliothekBerlin/ocrd_butler.git & cd ocrd-butler
  /home/ocrd/ocrd-butler > source ../ocrd_all/venv/bin/activate
  (venv) /home/ocrd/ocrd-butler > pip install -r requirements.txt
  (venv) /home/ocrd/ocrd-butler > pip install -r requirements-dev.txt
  (venv) /home/ocrd/ocrd-butler > python setup.py develop

Maybe there are more steps necessary, e.g.

.. code-block:: bash

  /home/ocrd > cd ocrd_all/ocrd_calamari
  /home/ocrd/ocrd_all/ocrd_calamari > python setup.py develop

This step maybe needed for ocrd_calamari, ocrd_segment, ocrd_keraslm and ocrd_anybaseocr.

For some modules in `ocrd_all`_ there are further files necessary,
e.g. trained models for the OCR itself. The folders on the server
can be overwritten it every single task.

* sbb_textline_detector

.. code-block:: bash

  > mkdir /data/sbb_textline_detector && cd /data/sbb_textline_detector
  > wget https://qurator-data.de/sbb_textline_detector/models.tar.gz
  > tar xfz models.tar.gz


* ocrd_calamari

.. code-block:: bash

  > mkdir /data/calamari_models && cd /data/calamari_models
  > wget https://qurator-data.de/calamari-models/GT4HistOCR/model.tar.xz
  > tar xf model.tar.xz

* ocrd_tesserocr

.. code-block:: bash

  > mkdir /data/tesseract_models && cd /data/tesseract_models
  > wget https://qurator-data.de/tesseract-models/GT4HistOCR/models.tar
  > tar xf models.tar
  > cp GT4HistOCR_2000000.traineddata /usr/share/tesseract-ocr/4.00/tessdata/


Start celery worker:

.. code-block:: bash

    ╰─$ TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata celery worker -A ocrd_butler.celery_worker.celery -E -l info

Start flower monitor:

.. code-block:: bash

    ╰─$ flower --broker redis://localhost:6379 --persistent=True --db=flower [--log=debug --url_prefix=flower]

Flower monitor: http://localhost:5555


Run the app:

.. code-block:: bash

    ╰─$ TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata FLASK_APP=ocrd_butler/app.py flask run
    or
    ╰─$ FLASK_APP=ocrd_butler/app.py flask run


If download of METS files fail - disable the proxy on local machines.

Swagger docs: http://localhost:5000/api


Run the tests:

.. code-block:: bash

    ╰─$ TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata py.test


Resources
---------
`Flask + Celery = how to. <https://medium.com/@frassetto.stefano/flask-celery-howto-d106958a15fe>`


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
  Otherwise we can search for all other tasks with the same work_id and present a UI to run against the chosen one.
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
