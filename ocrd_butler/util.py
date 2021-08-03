# -*- coding: utf-8 -*-

"""Utils module."""

import os
import json
import glob
import pathlib
import re
import logging.config
import xml.etree.ElementTree as ET


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


system_conf = '/data/ocrd-butler/logging.conf'
local_conf = f'{os.getcwd()}/logging.conf'

for conf in (system_conf, local_conf):
    if(os.path.exists(conf)):
        conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), conf))
        logging.config.fileConfig(conf_path)
        break
log = logging.getLogger(__name__)


def logger(name: str) -> logging.Logger:
    """ returns logger instance for given identifier.

    >>> l=logger(__name__); l.setLevel('WARN'); l
    <Logger ocrd_butler.util (WARNING)>

    """
    return logging.getLogger(name)


logging_conf_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '../logging.conf'))
logging.config.fileConfig(logging_conf_path)
log = logging.getLogger(__name__)


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


def to_json(data):
    if isinstance(data, str):
        data = data.replace("'", '"')
        data = json.loads(data)
    return data
