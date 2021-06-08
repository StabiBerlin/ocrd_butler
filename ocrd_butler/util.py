# -*- coding: utf-8 -*-

"""Utils module."""

import os
import json
import re
import logging.config

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


def camel_case_split(identifier):
    """CamelCase split"""
    matches = re.finditer(
        ".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)",
        identifier)
    return [m.group(0) for m in matches]


def host_url(request):
    return request.host_url
    #return "http://localhost:5000/"

def flower_url(request):
    if request.host_url.startswith("http://localhost"):
        return "http://locahost:5555"
    return f"{request.host_url}/flower"

def to_json(data):
    if isinstance(data, str):
        data = data.replace("'", '"')
        data = json.loads(data)
    return data
