# -*- coding: utf-8 -*-

"""Restplus model definitions."""

from flask_restplus import fields
from ocrd_butler.api.restplus import api


task_model = api.model("Task Model", {
    # "uuid": fields.String(
    #     title="ID",
    #     required = False,
    #     description="UUID of the task",
    #     help="We use the one from celery when we create this task."),
    "works_id": fields.String(
        title="Works ID",
        required = True,
        description="ID of the work",
        help="Can e.g. be a PPN or a SNP."),
    "mets_url": fields.String(
        title="METS URL",
        required = True,
        description="METS URL of the work",
        help="Full URL is required."),
    "file_grp": fields.String(
        title="File group",
        required = False,
        description="The file group in the METS file to start the processor chain with.",
        help="Defaults to 'DEFAULT'.",
        default="DEFAULT"),
    "tesseract_model": fields.String(
        title="Tesseract model",
        required = False,
        description="The model used to do the OCR processing.",
        help="Defaults to 'deu'.",
        default='deu'),
})

chain_model = api.model("Chain Model", {
    # "id": fields.String(
    #     title="ID",
    #     required = False,
    #     description="ID of the id",
    #     help="This will be created for you."),
    "name": fields.String(
        title="Name",
        required = True,
        description="A unique name for the chain",
        help="Be creative."),
    "description": fields.String(
        title="Descrition",
        required = False,
        description="Some more information what the chain is for and should accomplish.",
        help="Be as elaborative as needed."),
    "processors": fields.List(
        fields.String,
        title="Processors",
        required = True,
        min_items=1,
        unique=True,
        description="The processor to be used.",
        help="The processors will be executed in the given order."
    ),
})
