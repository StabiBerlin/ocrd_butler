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

