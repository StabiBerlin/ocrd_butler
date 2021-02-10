from ocrd_butler import config
from ocrd_butler.config import TestingConfig

from . import skip_in_test_profile


@skip_in_test_profile
def test_skip():
    assert config != TestingConfig
