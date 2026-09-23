from decimal import Decimal

import pytest

from vrf.adapters.outbound.ocr import adapter as mod
from vrf.adapters.outbound.ocr.adapter import OcrAfipAdapter
from vrf.adapters.outbound.ocr.imagen import ocr_disponible
from vrf.domain.enums import TipoAfip
from tests.test_ocr import _make_pdf

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

TEXTO_FACTURA = """
FACTURA A
Razón Social: Acme Proveedor S.A.
CUIT: 30-71234562-0
Punto de Venta: 0001
Comp. Nro: 00012345
Fecha de Emisión: 15/07/2026
Importe Neto Gravado: 100,00
IVA 21%: 21,00
Importe Total: 121,00
CAE N°: 12345678901234
"""


def _sin_ocr(monkeypatch) -> dict[str, int]:
    """Cuenta invocaciones al OCR para poder afirmar cuál camino se tomó."""
    llamadas = {"imagen": 0, "pdf": 0}

    def de_imagen(data: bytes) -> str:
        llamadas["imagen"] += 1
        return TEXTO_FACTURA

    def de_pdf(data: bytes) -> str:
        llamadas["pdf"] += 1
        return TEXTO_FACTURA

    monkeypatch.setattr(mod, "texto_de_imagen", de_imagen)
    monkeypatch.setattr(mod, "texto_de_pdf_escaneado", de_pdf)
    return llamadas


def test_foto_se_parsea_con_ocr(monkeypatch) -> None:
    llamadas = _sin_ocr(monkeypatch)

    r = OcrAfipAdapter().preview(JPEG, "image/jpeg")

    assert llamadas["imagen"] == 1
    assert r.cuit_emisor == "30712345620"
    assert r.total == Decimal("121.00")
    assert r.tipo_afip == TipoAfip.A


def test_imagen_se_detecta_aunque_el_mime_sea_generico(monkeypatch) -> None:
    llamadas = _sin_ocr(monkeypatch)

    r = OcrAfipAdapter().preview(PNG, "application/octet-stream")

    assert llamadas["imagen"] == 1
    assert r.cuit_emisor == "30712345620"


def test_pdf_con_texto_no_usa_ocr(monkeypatch) -> None:
    llamadas = _sin_ocr(monkeypatch)

    r = OcrAfipAdapter().preview(_make_pdf(TEXTO_FACTURA.replace("\n", " ")), "application/pdf")

    assert llamadas == {"imagen": 0, "pdf": 0}
    assert r.cuit_emisor == "30712345620"


def test_pdf_escaneado_cae_en_el_ocr(monkeypatch) -> None:
    llamadas = _sin_ocr(monkeypatch)

    r = OcrAfipAdapter().preview(_make_pdf(""), "application/pdf")

    assert llamadas["pdf"] == 1
    assert r.cuit_emisor == "30712345620"


def test_archivo_que_no_es_factura_no_inventa_nada() -> None:
    r = OcrAfipAdapter().preview(b"texto plano cualquiera", "text/plain")

    assert r.cuit_emisor is None
    assert r.total is None
    assert r.incompleto() is True


def test_imagen_ilegible_no_inventa_datos(monkeypatch) -> None:
    # Lo que devuelve Tesseract con una foto de costado o fuera de foco.
    ruido = "du Huog % “HUN O/991d epIpen 9707 60"
    monkeypatch.setattr(mod, "texto_de_imagen", lambda data: ruido)

    r = OcrAfipAdapter().preview(JPEG, "image/jpeg")

    assert r.punto_venta is None
    assert r.numero is None
    assert r.razon_social is None
    assert r.incompleto() is True


def test_sin_tesseract_el_preview_queda_vacio_sin_romper(monkeypatch) -> None:
    from vrf.adapters.outbound.ocr import imagen

    monkeypatch.setattr(imagen, "ocr_disponible", lambda: False)

    r = OcrAfipAdapter().preview(JPEG, "image/jpeg")

    assert r.cuit_emisor is None
    assert r.incompleto() is True


@pytest.mark.skipif(not ocr_disponible(), reason="Tesseract no está instalado")
def test_integracion_ocr_lee_una_factura_renderizada() -> None:
    from PIL import Image, ImageDraw

    from vrf.adapters.outbound.ocr.imagen import texto_de_imagen

    imagen = Image.new("RGB", (1200, 700), "white")
    dibujo = ImageDraw.Draw(imagen)
    for fila, linea in enumerate(TEXTO_FACTURA.strip().split("\n")):
        dibujo.text((40, 40 + fila * 55), linea, fill="black")
    from io import BytesIO

    buffer = BytesIO()
    imagen.save(buffer, format="PNG")

    texto = texto_de_imagen(buffer.getvalue())

    assert "FACTURA" in texto.upper()
