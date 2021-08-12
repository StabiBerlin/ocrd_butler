# -*- coding: utf-8 -*-

"""Utils module."""
from typing import Dict, List, Union

import os
import json
import glob
import pathlib
import re
import logging
import logging.config
import loguru
import xml.etree.ElementTree as ET
import yaml

from ocrd_utils.logging import initLogging


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

        loguru.logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class StreamToLogger(object):
    def __init__(self, log_level="INFO"):
        self.log_level = log_level

    def write(self, buf):
        import ipdb; ipdb.set_trace()
        for line in buf.rstrip().splitlines():
            loguru.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

# initialize ocrd logging
initLogging()

# configure logging to grep logging from other modules
logging.basicConfig(handlers=[InterceptHandler()], level=0)
logging.getLogger().handlers = [InterceptHandler()]
logging.getLogger(None).setLevel("DEBUG")

# initialize our logging via loguru
# system_conf = '/data/ocrd-butler/logging.conf'
# local_conf = f'{os.getcwd()}/logging.yaml'
# for conf in (system_conf, local_conf):
#     if(os.path.exists(conf)):
#         conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), conf))
#         with open(conf_path, 'rt') as f:
#             config = yaml.safe_load(f.read())
#             logging.config.dictConfig(config)
#             break
loguru.logger.add(f"/data/log/ocrd-butler.log")
logger = loguru.logger

# def logger(name: str) -> logging.Logger:
#     """ returns logger instance for given identifier.

#     >>> l=logger(__name__); l.setLevel('WARN'); l
#     <Logger ocrd_butler.util (WARNING)>

#     """
#     return loguru.logger
#     # return logging.getLogger(name)


def camel_case_split(identifier):
    """CamelCase split"""
    matches = re.finditer(
        ".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)",
        identifier)
    return [m.group(0) for m in matches]


def ocr_result_path(result_dir: str, path_part: str = "OCR-D-OCR") -> pathlib.Path:
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
