# -*- coding: utf-8 -*-

"""Our chain configuration and the predefined processor chains."""

from flask import jsonify
from flask_restplus import Resource

from ocrd_tesserocr.segment_region import TesserocrSegmentRegion
from ocrd_tesserocr.segment_line import TesserocrSegmentLine
from ocrd_tesserocr.segment_word import TesserocrSegmentWord
from ocrd_tesserocr.recognize import TesserocrRecognize

from ocrd_kraken.binarize import KrakenBinarize
from ocrd_kraken.segment import KrakenSegment
from ocrd_kraken.ocr import KrakenOcr


from ocrd_butler.api.restplus import api

PROCESSORS_CONFIG = {
    "TesserocrSegmentRegion": {
        "class": TesserocrSegmentRegion,
        "output_file_grp": "OCRD-SEGMENTREGION"
    },
    "TesserocrSegmentLine": {
        "class": TesserocrSegmentLine,
        "output_file_grp": "OCRD-SEGMENTLINE"
    },
    "TesserocrSegmentWord": {
        "class": TesserocrSegmentWord,
        "output_file_grp": "OCRD-SEGMENTWORD"

    },
    "TesserocrRecognize":  {
        "class": TesserocrRecognize,
        "output_file_grp": "OCRD-RECOGNIZE",
        "parameter": {
            "model": "deu",
            "overwrite_words": False,
            "textequiv_level": "line"
        }
    },
    "KrakenBinarize":  {
        "class": KrakenBinarize,
        "output_file_grp": "OCRD-KRAKEN-BINARIZE",
    },
    "KrakenSegment":  {
        "class": KrakenSegment,
        "output_file_grp": "OCRD-KRAKEN-SEGMENT",
    },
    "KrakenOcr":  {
        "class": KrakenOcr,
        "output_file_grp": "OCRD-KRAKEN-OCR",
    },
}

PROCESSOR_NAMES = PROCESSORS_CONFIG.keys()

PROCESSORS = []
for name, config in PROCESSORS_CONFIG.items():
    PROCESSORS.append({
        "name": name,
        "description": config["class"].__doc__,
        "output-file-group": config["output_file_grp"],
        "parameter": "" if "parameter" not in config else config["parameter"]
    })


ns = api.namespace("processors", description="The processors known by our butler.")

@ns.route("/processors")
class Processors(Resource):
    """Shows the processor configuration."""

    def get(self):
        return jsonify(PROCESSORS)
