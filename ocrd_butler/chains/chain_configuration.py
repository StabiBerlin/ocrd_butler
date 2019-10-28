# -*- coding: utf-8 -*-

"""Our chain configuration and the predefined processor chains."""

from ocrd_tesserocr.segment_region import TesserocrSegmentRegion
from ocrd_tesserocr.segment_line import TesserocrSegmentLine
from ocrd_tesserocr.segment_word import TesserocrSegmentWord
from ocrd_tesserocr.recognize import TesserocrRecognize


chain_config = {
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
        "output_file_grp": "SEGMENTWORD"

    },
    "TesserocrRecognize":  {
        "class": TesserocrRecognize,
        "output_file_grp": "RECOGNIZE",
        "parameter": {
            "model": "deu",
            "overwrite_words": False,
            "textequiv_level": "line"
        }
    },
}
