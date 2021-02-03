# -*- coding: utf-8 -*-

"""Restx initialization."""


from flask_restx import Api


api = Api(
    version="v1",
    title="ORC-D butler API",
    description="Friendly service to handle your daily OCR-D tasks.")
