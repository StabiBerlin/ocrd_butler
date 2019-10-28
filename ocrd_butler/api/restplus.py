# -*- coding: utf-8 -*-

"""Restplus initialization."""


from flask_restplus import Api, Resource, fields


api = Api(
    version="v1",
    title="ORC-D butler API",
    description="Friendly service to handle your daily OCR-D tasks.")
