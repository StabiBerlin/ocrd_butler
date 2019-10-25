# -*- coding: utf-8 -*-

"""Our predefined processor chains.

   We create different chains with a specific names and a description how
   (or for what) useful they seem and set one chain as default.
   If no chain or chain name was given while creating the task the default
   one has to be used.
"""

tesserocr_chain = {
    "name": "Tesserocr Chain",
    "description": "Basic OCR creation via Tesseract with binarization",
    "processors": [
        {"TesserocrSegmentRegion": {}},
        {"TesserocrSegmentLine": {}},
        {"TesserocrSegmentWord": {}},
        {"TesserocrRecognize": {}}
    ]
}

processor_chains = [
    tesserocr_chain,
]

default_chain = tesserocr_chain
