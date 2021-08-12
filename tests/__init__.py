import os
import json
from functools import partial
import subprocess
from itertools import filterfalse
from typing import Callable, Iterable, List, Type

import pytest

from ocrd_butler.util import logger
from ocrd_butler.config import Config
from ocrd_butler.database.models import (
    db,
    Workflow,
    Task,
)



def load_mock_db_model(
    model_class: Type[db.Model], root_node: str, filename: str
) -> Iterable:
    """ load example data from JSON file and instantiate model instances
    """
    with open(filename, 'r') as f:
        for i, data in enumerate(json.load(f)[root_node]):
            _id = data.pop('id', None)
            model_instance = model_class.create(**data)
            model_instance.id = _id or i + 1
            yield model_instance


load_mock_workflows = partial(load_mock_db_model, Workflow, 'workflows')
load_mock_tasks = partial(load_mock_db_model, Task, 'tasks')


def test_profile_active() -> bool:
    """ determine if in ``TEST`` profile, based on ``PROFILE`` env var.
    """
    return os.environ.get('PROFILE', '').lower() == 'test'


def ocrd_processor_available(processor: str) -> bool:
    """ checks whether or not processor executable can be found in environment,
    and is explicitly included in configuration.
    """
    if processor in Config.PROCESSORS:
        try:
            return subprocess.check_output(
                ['which', processor]
            ) is not None
        except Exception:
            logger.error(
                'No executable found for processor `%s`', processor
            )
            return False


def require_ocrd_processors(*processors: List[str]) -> Callable:
    """ decorator for tests that require specific OCRD processor executables.
    Translates to ``@pytest.mark.skipif`` decorator for allowing or skipping
    the test depending on the availability of *all* OCRD executables
    specified via parameter list. If no parameters are given, then *all*
    processors listed in the ``PROCESSORS`` attribute of
    :class:`~ocrd_butler.config.Config` must be available, otherwise the test
    will be skipped.
    """
    if len(processors) < 1:
        processors = Config.PROCESSORS
    not_available = list(
        filterfalse(
            ocrd_processor_available,
            processors
        )
    )

    def decorator(f) -> Callable:
        """ decorates given function with a ``pytest.mark.skipif`` decoration
        indicating whether any of the required OCRD processor executables
        are missing in the current environment, i.e. whether the function
        (i.e. test case) can't possibly succeed and must hence be skipped.
        """
        return pytest.mark.skipif(
            len(not_available) > 0,
            reason='Required OCRD processor(s) `{}` not found.'.format(
                ', '.join(not_available)
            )
        )(f)
    return decorator


skip_in_test_profile = partial(
    pytest.mark.skipif(
        test_profile_active(),
        reason='Test not supposed to be run in `TEST` profile.'
    )
)
