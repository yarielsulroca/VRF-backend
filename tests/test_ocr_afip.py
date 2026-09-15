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
