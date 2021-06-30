"""
Default configuration for the butler.
https://flask.palletsprojects.com/en/1.1.x/config/
"""

import os
import json
import subprocess

from .util import logger

log = logger(__name__)
DEFAULT_PROFILE = 'DEV'


def exec_processor_dump_json(processor: str) -> dict:
    """ tries to call processor with command line argument ``-J``
    (``--dump-json``) and return result, or throw exception if processor
    can not be found.

    Throws:
        FileNotFoundError
    """
    return json.loads(
        subprocess.check_output([processor, "-J"])
    )


class Config(object):
    """
    Base config, uses staging database server.
    """
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = None
    CELERY_RESULT_BACKEND_URL = "redis://localhost:6379"
    CELERY_BROKER_URL = "redis://localhost:6379"
    OCRD_BUTLER_RESULTS = "/data/ocrd_butler_results"
    SBB_CONTENT_SERVER_HOST = "content.staatsbibliothek-berlin.de"
    SBB_IIIF_FULL_TIF_URL = "https://content.staatsbibliothek-berlin.de/dc/"\
                            "{0}-{1}/full/full/0/default.tif"
    PROCESSORS = [
        "ocrd-calamari-recognize",

        "ocrd-olena-binarize",

        "ocrd-sbb-textline-detector",
        "ocrd-sbb-binarize",

        "ocrd-fileformat-transform",

        "ocrd-tesserocr-binarize",
        "ocrd-tesserocr-recognize",
        "ocrd-tesserocr-segment-table",
        "ocrd-tesserocr-crop",
        "ocrd-tesserocr-segment-line",
        "ocrd-tesserocr-segment-word",
        "ocrd-tesserocr-deskew",
        "ocrd-tesserocr-segment-region",

        "ocrd-keraslm-rate",

        "ocrd-segment-evaluate",
        "ocrd-segment-extract-regions",
        "ocrd-segment-repair",
        "ocrd-segment-extract-lines",
        "ocrd-segment-from-coco",
        "ocrd-segment-replace-original",
        "ocrd-segment-extract-pages",
        "ocrd-segment-from-masks",

        # "ocrd-anybaseocr-binarize",
        # "ocrd-anybaseocr-dewarp",
        # "ocrd-anybaseocr-block-segmentation",
        # "ocrd-anybaseocr-layout-analysis",
        # "ocrd-anybaseocr-crop",
        # "ocrd-anybaseocr-textline",
        # "ocrd-anybaseocr-deskew",
        # "ocrd-anybaseocr-tiseg",

        "ocrd-dinglehopper",

        "ocrd-pagetopdf",

        # "ocrd-make",

        "ocrd-pc-segmentation",

        "ocrd-preprocess-image",

        "ocrd-repair-inconsistencies",

        # "ocrd-cis-align",
        # "ocrd-cis-data",
        # "ocrd-cis-ocropy-binarize",
        # "ocrd-cis-ocropy-clip",
        # "ocrd-cis-ocropy-denoise",
        # "ocrd-cis-ocropy-deskew",
        # "ocrd-cis-ocropy-dewarp",
        # "ocrd-cis-ocropy-rec",
        # "ocrd-cis-ocropy-recognize",
        # "ocrd-cis-ocropy-resegment",
        # "ocrd-cis-ocropy-segment",
        # "ocrd-cis-ocropy-train",
        # "ocrd-cis-postcorrect",

        # "ocrd-cor-asv-ann-evaluate",
        # "ocrd-cor-asv-ann-process",

        # "ocrd-dummy",

        # "ocrd-export-larex",

        # "ocrd-im6convert",

        # "ocrd-typegroups-classifier",

        # "ocrd-import",

        # "ocrd-skimage-binarize",
        # "ocrd-skimage-denoise",
        # "ocrd-skimage-denoise-raw",
        # "ocrd-skimage-normalize",
    ]

    PROCESSOR_SETTINGS = {
        "ocrd-calamari-recognize": {
            "checkpoint_dir": "/data/ocrd-resources/ocrd-calamari-recognize/qurator-gt4histocr-1.0",
        },
        "ocrd-sbb-textline-detector": {
            "model": "/data/ocrd-resources/ocrd-sbb-textline-detector/default",
        },
        "ocrd-tesserocr-recognize": {
            "model": "Fraktur_GT4HistOCR",
        },
        "ocrd-olena-binarize": {
            "output_file_grp": ["OCR-D-IMG-BINPAGE"]
        },
        "ocrd-sbb-binarize": {
            "output_file_grp": ["OCR-D-IMG-BINPAGE"]
        },
        "ocrd-fileformat-transform": {
            "output_file_grp": ["OCR-D-OCR-ALTO"]
        },
    }


    @classmethod
    def processor_specs(cls, processor: str) -> dict:
        """ retrieve OCRD processor specification from its ``--dump-json``
        output and return it as a dict.

        Args:
            processor: name of a processor executable
        """
        try:
            return exec_processor_dump_json(processor)
        except FileNotFoundError:
            log.error('OCRD processor `%s` not found!', processor)
            return {}


class ProductionConfig(Config):
    """
    Uses production database server.
    """
    SQLALCHEMY_DATABASE_URI = 'sqlite:///./production.db'
    OCRD_BUTLER_RESULTS = "/data/ocrd_butler_results"


class DevelopmentConfig(Config):
    """
    Uses development database server.
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///./development.db'


class TestingConfig(Config):
    """
    Uses in memory database for testing.
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    OCRD_BUTLER_RESULTS = "/tmp/ocrd_butler_results_testing"
    SBB_CONTENT_SERVER_HOST = "foo.bar"

    @classmethod
    def processor_specs(cls, processor: str) -> dict:
        """ return fake processor specs from ``tests/files/processor_specs``
        resource folder in case the respective binary can't be found within
        actual environment (i.e. `ocrd_all` is not installed).
        """
        specs = super().processor_specs(processor)
        if len(specs) > 0:
            return specs

        filename = os.path.join(
            *'tests/files/processor_specs'.split('/'),
            '{}.json'.format(processor)
        )
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                specs = json.load(f)
            return specs
        else:
            log.warn(
                'file not found: {}'.format(filename)
            )
            return {}


def get_profile_var() -> str:
    """ get value of ``PROFILE`` environment variable or default to
    ``DEFAULT_PROFILE`` if not set or empty string.

    >>> os.environ['PROFILE'] = ''
    >>> get_profile_var()
    'DEV'

    >>> os.environ['PROFILE'] = 'prod'
    >>> get_profile_var()
    'PROD'

    """
    val = os.environ.get(
        "PROFILE", DEFAULT_PROFILE
    ).upper()
    if type(val) == str:
        if len(val.strip()) < 1:
            val = DEFAULT_PROFILE
    return val or DEFAULT_PROFILE


def profile_config() -> Config:
    """ select a ``Config`` implementation based on the ``PROFILE`` environment
    variable.

    >>> os.environ['PROFILE'] = 'PROD'
    >>> profile_config()
    <class 'ocrd_butler.config.ProductionConfig'>

    >>> os.environ['PROFILE'] = ''
    >>> profile_config()
    <class 'ocrd_butler.config.DevelopmentConfig'>

    """
    if 'PROFILE' in os.environ:
        log.debug(
            'Select config implementation based on PROFILE env var value `%s`',
            os.environ['PROFILE'],
        )
    else:
        log.warning(
            'Environment variable PROFILE not set. Defaulting to `%s`.',
            DEFAULT_PROFILE,
        )
    config = {
        "TEST": TestingConfig,
        "DEV": DevelopmentConfig,
        "PROD": ProductionConfig,
    }.get(
        get_profile_var()
    )
    log.info('Selected config: %s.', config)
    return config
