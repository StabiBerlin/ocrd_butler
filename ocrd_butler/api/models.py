# -*- coding: utf-8 -*-

"""Restx model definitions."""
import json

from flask_restx import fields
from ocrd_butler.api.restx import api


task_model = api.model("Task Model", {
    "works_id": fields.String(
        title="Works ID",
        required=True,
        description="ID of the work",
        help="Can e.g. be a PPN or a SNP."),
    "mets_url": fields.String(
        title="METS URL",
        required=True,
        description="METS URL of the work",
        help="Full URL is required."),
    "file_grp": fields.String(
        title="File group",
        required=False,
        description="The file group in the METS file to start the processor chain with.",
        help="Defaults to 'DEFAULT'.",
        default="DEFAULT"),
    "chain": fields.String(
        title="Processor chain",
        required=True,
        description="The chain of processors that will be used."),
    "parameter": fields.String(
        title="Parameter",
        required=False,
        description="Provide parameter for the processors."),
})


class ChainProcessorsField(fields.Raw):
    __schema_type__ = 'list'
    __schema_format__ = 'JSON'
    __schema_example__ = '["processor-1", "processor-2", ...]'

    def format(self, value):
        # return json.dumps(value)
        return value

class ChainParametersField(fields.Raw):
    __schema_type__ = 'dict'
    __schema_format__ = 'JSON'
    __schema_example__ = '{"processor-1": {"pamameter-1":"value-1", ...}, ...}'

    def format(self, value):
        # return json.dumps(value)
        return value


chain_model = api.model("Chain Model", {
    "name": fields.String(
        title="Name",
        required=True,
        description="A unique name for the chain",
        help="Be creative."),
    "description": fields.String(
        title="Descrition",
        required=False,
        description="Some more information what the chain is for and should accomplish.",
        help="Be as elaborative as needed."),
    "processors": fields.List(
        fields.String,
        title="Processors",
        required=True,
        min_items=1,
        unique=True,
        description="The processor to be used.",
        help="The processors will be executed in the given order."),
    "parameters": ChainParametersField(
        title="Parameters",
        required=False,
        unique=True,
        description="The default parameters for the processors.",
        help="The parameters will be use while running the processor. Can be overwritten in a task."),
})
