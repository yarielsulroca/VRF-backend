from datetime import date
from decimal import Decimal
from uuid import uuid4

from vrf.domain.agregados import (
    entra_compensacion,
    entra_kpi,
    entra_libro_iva,
    porcentaje,
    rango_mes,
    sumar_totales,
)
from vrf.domain.entities import Comprobante
from vrf.domain.enums import Clasificacion, EstadoPago, TipoAfip
from vrf.domain.exceptions import InvalidInput
from vrf.domain.vos import dinero
import pytest

E1 = uuid4()
OID = uuid4()


def _c(**kwargs) -> Comprobante:
    base = dict(
        id=uuid4(),
        empresa_id=E1,
        obra_id=OID,
        proveedor_id=None,
        usuario_id=uuid4(),
        clasificacion=Clasificacion.COMPRA,
        rubro_id=uuid4(),
        tipo_pago_id=None,
        tipo_afip=TipoAfip.A,
        punto_venta=1,
        numero=1,
        fecha=date(2026, 7, 10),
        neto_21=Decimal("100.00"),
        iva_21=Decimal("21.00"),
        neto_105=Decimal("0.00"),
        iva_105=Decimal("0.00"),
        neto_27=Decimal("0.00"),
        iva_27=Decimal("0.00"),
        no_gravado=Decimal("0.00"),
        percep_iva=Decimal("0.00"),
        percep_iibb=Decimal("0.00"),
        total=Decimal("121.00"),
        estado_pago=EstadoPago.COMPROBADO_PAGADO,
        cuit_emisor="33711174929",
    )
    base.update(kwargs)
    return Comprobante(**base)


def test_rango_mes() -> None:
    d, h = rango_mes("2026-07")
    assert d == date(2026, 7, 1)
    assert h == date(2026, 7, 31)


def test_rango_mes_invalido() -> None:
    with pytest.raises(InvalidInput):
        rango_mes("2026/07")


def test_pendiente_no_entra_kpi() -> None:
    d, h = rango_mes("2026-07")
    item = _c(estado_pago=EstadoPago.PENDIENTE)
    assert not entra_kpi(item, d, h)
    assert sumar_totales([c for c in [item] if entra_kpi(c, d, h)]) == dinero(0)


def test_comprobado_fuera_de_mes_no_entra() -> None:
    d, h = rango_mes("2026-09")
    item = _c(fecha=date(2026, 7, 31), estado_pago=EstadoPago.COMPROBADO_PAGADO)
    assert not entra_kpi(item, d, h)


def test_gasto_sin_obra_no_compensa() -> None:
    item = _c(obra_id=None)
    assert not entra_compensacion(item, OID)


def test_anulado_no_entra_libro() -> None:
    assert not entra_libro_iva(_c(estado_pago=EstadoPago.ANULADO))


def test_tipo_x_no_entra_libro() -> None:
    assert not entra_libro_iva(_c(tipo_afip=TipoAfip.X))


def test_pendiente_abc_entra_libro() -> None:
    assert entra_libro_iva(_c(estado_pago=EstadoPago.PENDIENTE, tipo_afip=TipoAfip.B))


def test_porcentaje() -> None:
    assert porcentaje(Decimal("121.00"), Decimal("242.00")) == Decimal("50.0")
