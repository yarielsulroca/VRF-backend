from vrf.adapters.outbound.ocr.afip import parse_afip_text
from vrf.adapters.outbound.ocr.imagen import texto_de_imagen, texto_de_pdf_escaneado
from vrf.adapters.outbound.ocr.pdf import extract_pdf_text_bytes
from vrf.domain.ports.ocr import OcrResultado

# Un PDF de AFIP con texto embebido ronda los miles de caracteres. Por debajo de
# esto es un escaneo (o trae solo un sello suelto) y hay que rasterizarlo.
_MINIMO_TEXTO_PDF = 120

_FIRMAS_IMAGEN = (b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"BM", b"II*\x00", b"MM\x00*")

# Una imagen ilegible no devuelve texto vacío: devuelve ruido, y de ese ruido el
# parser puede sacar un número de comprobante inventado. Sin estas señales,
# preferimos no extraer nada.
_SENALES_FACTURA = (
    "cuit",
    "factura",
    "importe",
    "punto de venta",
    "comp",
    "iva",
    "cae",
    "total",
)
_MINIMO_SENALES = 3


def _es_pdf(data: bytes, mime: str) -> bool:
    return "pdf" in mime or data[:4] == b"%PDF"


def _es_imagen(data: bytes, mime: str) -> bool:
    if mime.startswith("image/"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return any(data.startswith(firma) for firma in _FIRMAS_IMAGEN)


def _con_texto(texto: str) -> bool:
    return len("".join(texto.split())) >= _MINIMO_TEXTO_PDF


def _parece_factura(texto: str) -> bool:
    bajo = texto.lower()
    return sum(1 for senal in _SENALES_FACTURA if senal in bajo) >= _MINIMO_SENALES


def _parsear_ocr(texto: str) -> OcrResultado:
    return parse_afip_text(texto) if _parece_factura(texto) else OcrResultado()


class OcrAfipAdapter:
    def preview(self, data: bytes, mime: str) -> OcrResultado:
        mime = (mime or "").lower()
        if _es_pdf(data, mime):
            texto = extract_pdf_text_bytes(data)
            if _con_texto(texto):
                return parse_afip_text(texto)
            return _parsear_ocr(texto_de_pdf_escaneado(data))
        if _es_imagen(data, mime):
            return _parsear_ocr(texto_de_imagen(data))
        return OcrResultado()
