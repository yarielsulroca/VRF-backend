from vrf.adapters.outbound.ocr.afip import parse_afip_text
from vrf.adapters.outbound.ocr.pdf import extract_pdf_text_bytes
from vrf.domain.ports.ocr import OcrResultado


class OcrAfipAdapter:
    def preview(self, data: bytes, mime: str) -> OcrResultado:
        es_pdf = "pdf" in (mime or "").lower() or data[:4] == b"%PDF"
        if not es_pdf:
            return OcrResultado()
        return parse_afip_text(extract_pdf_text_bytes(data))
