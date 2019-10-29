# -*- coding: utf-8 -*-

"""Restplus model definitions."""

from flask_restplus import fields
from ocrd_butler.api.restplus import api


task_model = api.model("Task Model", {
    "id": fields.String(
            required = True,
            description="ID of the work",
            help="Can e.g. be a PPN or a SNP."),
    "mets_url": fields.String(
            required = True,
            description="METS URL of the work",
            help="Full URL is required."),
    "file_grp": fields.String(
            required = False,
            description="The file group in the METS file to start the process chain with.",
            help="Defaults to 'DEFAULT'.",
            default="DEFAULT"),
    "tesseract_model": fields.String(
            required = False,
            description="The model used to do the OCR processing.",
            help="Defaults to 'deu'.",
            default='deu'),
})
