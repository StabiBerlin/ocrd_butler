"""
Default configuration for the butler.
https://flask.palletsprojects.com/en/1.1.x/config/
"""

import os
import json
import subprocess


class Config(object):
    """
    Base config, uses staging database server.
    """
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = None
    CELERY_RESULT_BACKEND_URL = "redis://localhost:6379"
    CELERY_BROKER_URL = "redis://localhost:6379"
    OCRD_BUTLER_RESULTS = "/tmp/ocrd_butler_results"
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

        "ocrd-anybaseocr-binarize",
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

    @classmethod
    def processor_specs(cls, processor: str) -> dict:
        """ retrieve OCRD processor specification from its ``--dump-json`` output
        and return it as a dict.

        Args:
            processor: name of a processor executable
        """
        return json.loads(
            subprocess.check_output([processor, "-J"])
        )


class ProductionConfig(Config):
    """
    Uses production database server.
    """
    SQLALCHEMY_DATABASE_URI = 'sqlite:///./production.db'


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

    @classmethod
    def processor_specs(cls, processor: str) -> dict:
        """ return fake processor specs from
        ``tests/files/processor_specs`` resource folder in case the respective
        binary can't be found within actual environment (i.e. `ocrd_all` is not installed).
        """
        try:
            return super().processor_specs(processor)
        except Exception:
            pass

        filename = os.path.join(
            *'tests/files/processor_specs'.split('/'),
            '{}.json'.format(processor)
        )
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                specs = json.load(f)
            return specs
        else:
            print(
                'file not found: {}'.format(filename)
            )
            return {}


def profile_config() -> Config:
    """ select a ``Config`` implementation based on the ``PROFILE`` environment variable
    """
    return {
        "test": TestingConfig,
        "dev": DevelopmentConfig,
        "prod": ProductionConfig,
    }.get(
        os.environ.get(
            "PROFILE", "DEV"
        ).lower()
    )
