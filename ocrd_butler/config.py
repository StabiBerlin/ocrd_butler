"""
Default configuration for the butler.
https://flask.palletsprojects.com/en/1.1.x/config/
"""


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
