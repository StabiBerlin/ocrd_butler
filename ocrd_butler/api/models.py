# -*- coding: utf-8 -*-

"""Restx model definitions."""

from flask_restx import fields
from ocrd_butler.api.restx import api

task_model = api.model("Task Model", {
    "src": fields.String(
        title="Source",
        required=True,
        description="URL to a METS file or filename of an image or an archive with images.",
        help="A source is required."),
    "workflow_id": fields.String(
        title="Processor workflow",
        required=True,
        description="The workflow of processors that will be used."),
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
        description="The default file group in the METS file to start the processor workflow with.",
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

class WorkflowProcessors(fields.Raw):
    __schema_type__ = 'array'
    __schema_format__ = 'JSON'
    __schema_example__ = '''[
            {
                'ocrd-processor-0': {}
            },
            {
                'ocrd-processor-n': {
                    'parameter-name-0': 'parameter-value-0',
                    'parameter-name-n': 'parameter-value-n',
                }
            }
        ]
    '''
    # min_items=1,
    def format(self, value):
        # return json.dumps(value)
        return value

workflow_model = api.model("Workflow Model", {
    "name": fields.String(
        title="Name",
        required=True,
        description="A unique name for the workflow",
        help="Be creative."),
    "description": fields.String(
        title="Description",
        required=False,
        description="Some more information what the workflow should fulfil.",
        help="Be as elaborative as needed."),
    "processors": WorkflowProcessors(
        title="Processors",
        required=True,
        min_items=1,
        unique=False,
        description="The processors to be used in the workflow.",
        help="The processors will be executed in the given order. The parameters will be filled up with the defaults. Can be overwritten in a task."),
})
