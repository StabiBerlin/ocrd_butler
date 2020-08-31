""" Default configuration for the butler.
    https://flask.palletsprojects.com/en/1.1.x/config/
"""


class Config(object):
    """Base config, uses staging database server."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = None
    CELERY_RESULT_BACKEND_URL = "redis://localhost:6379"
    CELERY_BROKER_URL = "redis://localhost:6379"
    OCRD_BUTLER_RESULTS = "/tmp/ocrd_butler_results"
    DIRECT_PROCESSOR_SCRIPTS = [
        "/srv/ocrd_all/ocrd_olena",
        "/srv/ocrd_all/dinglehopper",
        "/srv/ocrd_all/sbb_textline_detector",
        "/srv/ocrd_all/ocrd_fileformat"
    ]
    PROCESSOR_PACKAGES = [
        "ocrd_tesserocr",
        "ocrd_calamari",
        "ocrd_segment",
        "ocrd_keraslm",
        "ocrd_anybaseocr"
    ]

class ProductionConfig(Config):
    """Uses production database server."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///./production.db'

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///./development.db'

class TestingConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    OCRD_BUTLER_RESULTS = "/tmp/ocrd_butler_results_testing"

