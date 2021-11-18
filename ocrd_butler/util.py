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

from ocrd_page_to_alto.convert import OcrdPageAltoConverter
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


def ocr_result_path(task_result_dir: str, path_part: tuple = ("RECOGNIZE", "CALAMARI")) -> pathlib.Path:
    """ Get base path to the page xml results of the task. """
    result_xml_files = glob.glob(f"{task_result_dir}/*/*.xml")
    for _file in result_xml_files:
        if not any(part in _file for part in path_part):  # This is a bit fixed.
            continue
        tree = ET.parse(_file)
        xmlns = tree.getroot().tag.split("}")[0].strip("{")
        if xmlns in page_xml_namespaces.values():
            if tree.findall(".//pc:Unicode", {"pc": xmlns}):
                return pathlib.Path(os.path.dirname(_file))


def alto_result_path(task_result_dir: str) -> pathlib.Path:
    alto_result_dir = f"{task_result_dir}/OCR-D-OCR-ALTO"
    if not os.path.exists(alto_result_dir):
        os.mkdir(alto_result_dir)
    return pathlib.Path(alto_result_dir)


def page_to_alto(uid: str, task_result_dir: str):
    """ Convert page files to alto. """
    page_result_path = ocr_result_path(task_result_dir)

    if page_result_path is None:
        logger.info(f"Can't find page results to create alto for task {uid}.")
        return

    alto_path = alto_result_path(task_result_dir)
    for file_path in page_result_path.iterdir():
        converter = OcrdPageAltoConverter(
            check_words=False,
            check_border=False,
            page_filename=file_path
        )
        alto_xml = converter.convert()
        alto_file_name = file_path.name.replace("CALAMARI", "ALTO")
        alto_result_file = alto_path.joinpath(alto_file_name)
        with open(alto_result_file, "w") as alto_file:
            alto_file.write(str(alto_xml))

    logger.info(f"Created alto from page for task {uid}.")


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
