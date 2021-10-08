# -*- coding: utf-8 -*-

"""Utils module."""

from typing import Dict, List, Union

import os
import json
import glob
import pathlib
import re
import logging
import loguru
import xml.etree.ElementTree as ET

from ocrd_utils.logging import initLogging

from . import config


page_xml_namespaces = {
    "page_2009-03-16": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2009-03-16",
    "page_2010-01-12": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2010-01-12",
    "page_2010-03-19": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2010-03-19",
    "page_2013-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15",
    "page_2016-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2016-07-15",
    "page_2017-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15",
    "page_2018-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2018-07-15",
    "page_2019-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"
}


class InterceptHandler(logging.Handler):
    """ Handler can be added to existing logging configuration
        of other modules to get its logging messages.
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = loguru.logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        loguru.logger.opt(depth=depth, exception=record.exc_info)\
                     .log(level, record.getMessage())


class StreamToLogger(object):
    """ Fake input and output streams for other processes to
        get the logging messages.
    """
    def __init__(self, level="INFO"):
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            loguru.logger.log(self.level, line.rstrip())

    def flush(self):
        pass

# Initialize ocrd logging because we want to have this before
# we start logging our stuff.
initLogging()


# Configure logging to grep logging from other modules.
logging.basicConfig(handlers=[InterceptHandler()], level=0)
logging.getLogger().handlers = [InterceptHandler()]
logging.getLogger(None).setLevel("DEBUG")

# Initialize our logging via loguru.
loguru.logger.add(
    f"{config.LOGGER_PATH}/ocrd-butler.log",
    rotation="06:00",
    retention="20 days",
    compression="gz")
# If we start as service allow logging for other users.
try:
    os.chmod(f"{config.LOGGER_PATH}/ocrd-butler.log", 0o766)
except PermissionError:
    pass
logger = loguru.logger


def camel_case_split(identifier):
    """CamelCase split"""
    matches = re.finditer(
        ".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)",
        identifier)
    return [m.group(0) for m in matches]


def ocr_result_path(result_dir: str, path_part: str = "OCR") -> pathlib.Path:
    """ Get base path to the page xml results of the task. """
    result_xml_files = glob.glob(f"{result_dir}/*/*.xml")
    for file in result_xml_files:
        if not path_part in file:  # This is a bit fixed.
            continue
        tree = ET.parse(file)
        xmlns = tree.getroot().tag.split("}")[0].strip("{")
        if xmlns in page_xml_namespaces.values():
            return pathlib.Path(os.path.dirname(file))


def host_url(request):
    return request.host_url
    # return "http://localhost:5000/"


def flower_url(request):
    if request.host_url.startswith("http://localhost"):
        return "http://localhost:5555"
    return f"{request.host_url}/flower"


def to_json(data: str) -> Union[Dict, List]:
    """ deserialize string, after replacing all occurrences of single quotes
    with double quotes. If input is not a string, it is being returned as-is.
    """
    if isinstance(data, str):
        data = data.replace("'", '"')
        data = json.loads(data)
    return data
