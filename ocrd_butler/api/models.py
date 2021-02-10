# -*- coding: utf-8 -*-

"""Restx model definitions."""

from flask_restx import fields
from ocrd_butler.api.restx import api

task_model = api.model("Task Model", {
    "uid": fields.String(
        title="UID",
        required=True,
        description="UID of the task",
        help="Unique id used interal."),
    "src": fields.String(
        title="Source",
        required=True,
        description="URL to a METS file or filename of an image or an archive with images.",
        help="A source is required."),
    "chain_id": fields.String(
        title="Processor chain",
        required=True,
        description="The chain of processors that will be used."),
    "description": fields.String(
        title="Description",
        required=False,
        description="Some more information what the task should fulfil.",
        help="Be as elaborative as needed."),
    "parameters": fields.String(
        title="Parameters",
        required=False,
        description="Provide parameter for the processors."),
    "default_file_grp": fields.String(
        title="Default file group",
        required=False,
        description="The default file group in the METS file to start the processor chain with.",
        help="Defaults to 'DEFAULT'.",
        default="DEFAULT"),
    "worker_task_id": fields.String(
        title="Worker Task ID",
        required=False,
        description="ID of the worker task, used to get state and result for the async task."),
    "status": fields.String(
        title="Status",
        required=False,
        description="Current status of the task.",
        default="CREATED"),
    "results": fields.String(
        title="Results",
        required=False,
        description="Results of a processed task.",
        default={}),
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
        title="Description",
        required=False,
        description="Some more information what the chain should fulfil.",
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
        default={},
        description="The default parameters for the processors.",
        help="The parameters will be use while running the processor. Can be overwritten in a task."),
})
