from decimal import Decimal

import pytest

from vrf.adapters.outbound.ocr.afip import parse_afip_text, parse_importe
from vrf.application.use_cases.ocr import PreviewOcr
from vrf.domain.entities import Proveedor, Usuario
from vrf.domain.enums import Rol, TipoAfip
from vrf.domain.exceptions import InvalidInput
from vrf.domain.ports.ocr import OcrResultado

TEXTO_AFIP = """
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


# Factura C real: pypdf emite las etiquetas y los valores en bloques separados
# porque el PDF de AFIP está maquetado en columnas.
TEXTO_COLUMNAS = """
Fecha de Emisión:
ORIGINAL
SULROCA GONZALEZ YARIEL
Pedro Nolasco Carrion 480 Dpto:408 -
Período Facturado Desde: Hasta: Fecha de Vto. para el pago:
Condición frente al IVA:
Apellido y Nombre / Razón Social:
Domicilio:
11/09/2026 11/09/2026 11/09/2026
27963709973
VRF S.A.
CUIT:
Punto de Venta: Comp. Nro:00001 00000027
Razón Social:
FACTURACCOD. 011
Responsable Monotributo
27963709973
CUIT: 33711174929
0,00
63550,00
63550,00
Subtotal: $
Importe Otros Tributos: $
Importe Total: $
CAE N°:
Fecha de Vto. de CAE:
Comprobante Autorizado
21/09/2026
86372611526307
"SULROCA GONZALEZ YARIEL"
"""


# Salida real de Tesseract sobre la misma factura escaneada: respeta el layout
# visual, así que etiqueta y valor caen juntos, con "$" en el medio.
TEXTO_OCR = """
ORIGINAL
COD. 011
Punto de Venta: 00001 Comp. Nro: 00000027
Razón Social: SULROCA GONZALEZ YARIEL Fecha de Emisión: 11/09/2026
Domicilio Comercial: Pedro Nolasco Carrion 480 Dpto:408 - CUIT: 27963709973
Condición frente al IVA: Responsable Monotributo
CUIT: 33711174929 Apellido y Nombre / Razón Social: VRF S.A.
Subtotal: $ 63550,00
Importe Otros Tributos: $ 0,00
Importe Total: $ 63550,00
"SULROCA GONZALEZ YARIEL"
ARCA Pág. 1/1 CAE N°: 86372611526307
"""


def test_parse_importe_argentino() -> None:
    assert parse_importe("1.234,56") == Decimal("1234.56")
    assert parse_importe("121,00") == Decimal("121.00")


def test_parse_afip_extrae_si_esta() -> None:
    r = parse_afip_text(TEXTO_AFIP)
    assert r.cuit_emisor == "30712345620"
    assert r.razon_social and "Acme" in r.razon_social
    assert r.tipo_afip == TipoAfip.A
    assert r.punto_venta == 1
    assert r.numero == 12345
    assert r.fecha and r.fecha.isoformat() == "2026-07-15"
    assert r.neto_21 == Decimal("100.00")
    assert r.iva_21 == Decimal("21.00")
    assert r.total == Decimal("121.00")
    assert r.cae == "12345678901234"
    assert r.incompleto() is False


def test_parse_afip_layout_en_columnas() -> None:
    r = parse_afip_text(TEXTO_COLUMNAS)
    assert r.cuit_emisor == "27963709973"
    assert r.razon_social == "SULROCA GONZALEZ YARIEL"
    assert r.tipo_afip == TipoAfip.C
    assert r.punto_venta == 1
    assert r.numero == 27
    assert r.fecha and r.fecha.isoformat() == "2026-09-11"
    assert r.total == Decimal("63550.00")
    assert r.cae == "86372611526307"
    assert r.incompleto() is False


def test_parse_afip_texto_de_ocr() -> None:
    r = parse_afip_text(TEXTO_OCR)
    assert r.cuit_emisor == "27963709973"
    assert r.razon_social == "SULROCA GONZALEZ YARIEL"
    assert r.tipo_afip == TipoAfip.C
    assert r.punto_venta == 1
    assert r.numero == 27
    assert r.fecha and r.fecha.isoformat() == "2026-09-11"
    assert r.cae == "86372611526307"
    # No debe confundir "Otros Tributos: $ 0,00" con el total.
    assert r.total == Decimal("63550.00")


def test_total_en_cero_se_descarta() -> None:
    r = parse_afip_text("FACTURA B\nCUIT: 30-71234562-0\nImporte Total: $ 0,00\n")
    assert r.total is None


def test_razon_social_no_toma_la_etiqueta_siguiente() -> None:
    r = parse_afip_text("Razón Social:\nDomicilio:\nCondición frente al IVA:\n")
    assert r.razon_social is None


def test_no_inventa_total() -> None:
    texto = """
    FACTURA B
    CUIT: 30-71234562-0
    Importe Neto Gravado: 100,00
    IVA 21%: 21,00
    """
    r = parse_afip_text(texto)
    assert r.total is None
    assert r.neto_21 == Decimal("100.00")


def test_cuit_invalido_se_ignora() -> None:
    r = parse_afip_text("CUIT: 20-12345678-9 FACTURA A")
    assert r.cuit_emisor is None


def test_vacio() -> None:
    r = parse_afip_text("   ")
    assert r.incompleto() is True
    assert r.cuit_emisor is None
    assert r.total is None


class FakeUow:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class FakeGrupos:
    def get_unico(self):
        from uuid import uuid4

        return uuid4(), "VRF"


class FakeProveedores:
    def __init__(self) -> None:
        self.items: list[Proveedor] = []

    def get_by_cuit(self, cuit: str):
        return next((p for p in self.items if p.cuit == cuit), None)

    def add(self, item: Proveedor) -> None:
        self.items.append(item)


class FakeOcr:
    def __init__(self, resultado: OcrResultado) -> None:
        self.resultado = resultado

    def preview(self, data: bytes, mime: str) -> OcrResultado:
        return self.resultado


def _admin() -> Usuario:
    from uuid import uuid4

    return Usuario(id=uuid4(), grupo_id=uuid4(), email="a@x", password_hash="h", rol=Rol.ADMIN)


def test_preview_crea_proveedor() -> None:
    from uuid import uuid4

    proveedores = FakeProveedores()
    resultado = OcrResultado(
        cuit_emisor="30712345620",
        razon_social="Acme",
        tipo_afip=TipoAfip.A,
        punto_venta=1,
        numero=1,
        total=Decimal("121"),
        neto_21=Decimal("100"),
        iva_21=Decimal("21"),
    )
    out = PreviewOcr(FakeOcr(resultado), proveedores, FakeGrupos(), FakeUow()).execute(
        _admin(), b"%PDF", "application/pdf"
    )
    assert out["proveedor_creado"] is True
    assert out["proveedor_id"]
    assert len(proveedores.items) == 1


def test_preview_iva_no_cuadra() -> None:
    resultado = OcrResultado(
        cuit_emisor="30712345620",
        total=Decimal("999"),
        neto_21=Decimal("100"),
        iva_21=Decimal("21"),
    )
    with pytest.raises(InvalidInput):
        PreviewOcr(FakeOcr(resultado), FakeProveedores(), FakeGrupos(), FakeUow()).execute(
            _admin(), b"%PDF", "application/pdf"
        )
