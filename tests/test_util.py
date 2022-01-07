import os

from ocrd_butler.util import (
    ocr_result_path,
    alto_result_path,
)


CURRENT_DIR = os.path.dirname(__file__)


class UtilTests():

    def test_util_ocr_result_path(self):
        result_dir = f"{CURRENT_DIR}/files/ocr_result_03"
        path = ocr_result_path(result_dir)
        assert path is not None
        assert path.exists() is True
        assert path.name == "03-OCRD-TESSEROCR-RECOGNIZE-OUTPUT"

    def test_util_alto_result_path(self):
        result_dir = f"{CURRENT_DIR}/files/ocr_result_03"
        path = alto_result_path(result_dir)
        assert path is not None
        assert path.exists() is True
        assert path.name == "04-OCRD-FILEFORMAT-TRANSFORM-OUTPUT"

        result_dir = f"{CURRENT_DIR}/files/ocr_result_04"
        path = alto_result_path(result_dir)
        assert path is not None
        assert path.exists() is True
        assert path.name == "OCR-D-OCR-ALTO"
