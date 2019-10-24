from ocrd_tesserocr.segment_region import TesserocrSegmentRegion
from ocrd_tesserocr.segment_line import TesserocrSegmentLine
from ocrd_tesserocr.segment_word import TesserocrSegmentWord
from ocrd_tesserocr.recognize import TesserocrRecognize


chain_config = {
    "TesserocrSegmentRegion": {
        "class": TesserocrSegmentRegion,
        "output_file_grp": "SEGMENTREGION"
    },
    "TesserocrSegmentLine": {
        "class": TesserocrSegmentLine,
        "output_file_grp": "SEGMENTLINE"
    },
    "TesserocrSegmentWord": {
        "class": TesserocrSegmentWord,
        "output_file_grp": "SEGMENTWORD"

    },
    "TesserocrRecognize":  {
        "class": TesserocrRecognize,
        "output_file_grp": "RECOGNIZE"

    },
}


# create different chains with a specific name and a description how (or for what) useful they seem
# set one chain as default, if no chain or chain name was given while creating the task
tesserocr_chain = [
    {"processor": "TesserocrSegmentRegion"},
    {"processor": "TesserocrSegmentLine"},
    {"processor": "TesserocrSegmentWord"},
    {
        "processor": "TesserocrRecognize",
        "parameters": {
            "model": "task_tesseract_model",
            "overwrite_words": False,
            "textequiv_level": "line"
        }
    }
]
