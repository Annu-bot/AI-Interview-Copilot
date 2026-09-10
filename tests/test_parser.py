import pytest
from ai_apps.src.parser import DocumentParser
from ai_apps.core.exceptions import DocumentParsingError


def test_clean_text():
    service = DocumentParser()
    raw = "Hello \xa0 world!   \n\n\n\nThis is a    test. \r\n"
    cleaned = service.clean_text(raw)
    assert "Hello world!" in cleaned
    assert "This is a test." in cleaned
    assert "\n\n\n" not in cleaned


def test_parse_text_file():
    service = DocumentParser()
    text_bytes = b"Software Engineer Resume\nPython, FastAPI, Docker"
    extracted = service.parse_text(text_bytes)
    assert "Software Engineer Resume" in extracted
    assert "FastAPI" in extracted


def test_unsupported_extension():
    service = DocumentParser()
    with pytest.raises(DocumentParsingError, match="Unsupported file format"):
        service.extract_text_from_upload("image.png", b"fake binary")
