from flask_restplus import Api, Resource, fields
from flask import current_app

# flask-restplus configuration
app = Api(
    app = current_app,
    version="v1",
    title="ORC-D Tasks",
    description="OCR-D Tasks API")

name_space = app.namespace(
    "ocrd-tasks",
    description="Manage OCR-D Tasks")

task_model = app.model("Task Model", {
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
