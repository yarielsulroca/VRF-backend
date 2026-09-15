from vrf.adapters.outbound.ocr.adapter import OcrAfipAdapter
from vrf.adapters.outbound.ocr.pdf import extract_pdf_text, extract_pdf_text_bytes
from vrf.adapters.outbound.ocr.afip import parse_afip_text

__all__ = ["OcrAfipAdapter", "extract_pdf_text", "extract_pdf_text_bytes", "parse_afip_text"]