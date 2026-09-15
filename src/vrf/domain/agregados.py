import calendar
from datetime import date
from decimal import Decimal
from uuid import UUID

from vrf.domain.entities import Comprobante, Usuario
from vrf.domain.enums import EstadoPago, Rol, TipoAfip
from vrf.domain.exceptions import InvalidInput
from vrf.domain.vos import dinero

_CERO = Decimal("0.00")
_PCT = Decimal("0.1")
_TIPOS_LIBRO = (TipoAfip.A, TipoAfip.B, TipoAfip.C)


def rango_mes(mes: str) -> tuple[date, date]:
    partes = mes.split("-")
    if len(partes) != 2:
        raise InvalidInput("Mes inválido (YYYY-MM)")
    try:
        anio, mes_n = int(partes[0]), int(partes[1])
        ultimo = calendar.monthrange(anio, mes_n)[1]
        return date(anio, mes_n, 1), date(anio, mes_n, ultimo)
    except ValueError as exc:
        raise InvalidInput("Mes inválido (YYYY-MM)") from exc


def en_periodo(fecha: date, desde: date, hasta: date) -> bool:
    return desde <= fecha <= hasta


def es_comprobado(item: Comprobante) -> bool:
    return item.estado_pago == EstadoPago.COMPROBADO_PAGADO


def entra_kpi(item: Comprobante, desde: date, hasta: date) -> bool:
    return es_comprobado(item) and en_periodo(item.fecha, desde, hasta)


def entra_compensacion(item: Comprobante, obra_id: UUID) -> bool:
    return es_comprobado(item) and item.obra_id == obra_id


def entra_libro_iva(item: Comprobante) -> bool:
    return item.tipo_afip in _TIPOS_LIBRO and item.estado_pago != EstadoPago.ANULADO


def visible_para(actor: Usuario, empresa_id: UUID) -> bool:
    if actor.rol == Rol.ADMIN:
        return True
    return empresa_id in actor.empresa_ids


def filtrar_visibles(actor: Usuario, items: list[Comprobante]) -> list[Comprobante]:
    return [c for c in items if visible_para(actor, c.empresa_id)]


def neto_sin_iva(item: Comprobante) -> Decimal:
    return dinero(item.neto_21 + item.neto_105 + item.neto_27 + item.no_gravado)


def solo_impuestos(item: Comprobante) -> Decimal:
    return dinero(item.iva_21 + item.iva_105 + item.iva_27 + item.percep_iva + item.percep_iibb)


def sumar_totales(items: list[Comprobante]) -> Decimal:
    return dinero(sum((c.total for c in items), _CERO))


def porcentaje(parte: Decimal, total: Decimal) -> Decimal:
    if total == _CERO:
        return dinero(_CERO)
    return (parte * Decimal("100") / total).quantize(_PCT)
