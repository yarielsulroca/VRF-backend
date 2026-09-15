from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(path: str) -> str:
    return _text_from_reader(PdfReader(path))


def extract_pdf_text_bytes(data: bytes) -> str:
    return _text_from_reader(PdfReader(BytesIO(data)))


def _text_from_reader(reader: PdfReader) -> str:
    return "\n".join(page.extract_text() or "" for page in reader.pages)