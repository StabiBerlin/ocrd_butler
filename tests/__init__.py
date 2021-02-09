import os
from functools import partial

import pytest


def test_profile_active():
    return os.environ.get('PROFILE', '').lower() == 'test'


requires_ocrd_all = partial(
    pytest.mark.skipif(
        test_profile_active(),
        reason='Test requires full OCRD-All installation'
    )
)
