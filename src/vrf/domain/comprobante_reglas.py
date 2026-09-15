from decimal import Decimal
from uuid import UUID

from vrf.domain.entities import Obra, Usuario
from vrf.domain.enums import Clasificacion, EstadoPago, Rol, TipoAfip
from vrf.domain.exceptions import Forbidden, InvalidInput
from vrf.domain.vos import ClaveAfip, dinero


def exigir_empresa_actor(actor: Usuario, empresa_id: UUID) -> None:
    if actor.rol == Rol.ADMIN:
        return
    if empresa_id not in actor.empresa_ids:
        raise Forbidden("No podés operar esa empresa")


def validar_clasificacion(
    clasificacion: Clasificacion, rubro_id: UUID | None, tipo_pago_id: UUID | None
) -> None:
    if clasificacion in (Clasificacion.COMPRA, Clasificacion.COSTO):
        if rubro_id is None:
            raise InvalidInput("Compra y costo exigen rubro")
        if tipo_pago_id is not None:
            raise InvalidInput("Compra y costo no llevan tipo de pago")
        return
    if clasificacion == Clasificacion.PAGO:
        if tipo_pago_id is None:
            raise InvalidInput("Pago exige tipo de pago")
        if rubro_id is not None:
            raise InvalidInput("Pago no lleva rubro")


def validar_iva(
    neto_21,
    iva_21,
    neto_105,
    iva_105,
    neto_27,
    iva_27,
    no_gravado,
    percep_iva,
    percep_iibb,
    total,
) -> None:
    partes = (
        dinero(neto_21)
        + dinero(iva_21)
        + dinero(neto_105)
        + dinero(iva_105)
        + dinero(neto_27)
        + dinero(iva_27)
        + dinero(no_gravado)
        + dinero(percep_iva)
        + dinero(percep_iibb)
    )
    tot = dinero(total)
    if partes != Decimal("0.00") and partes != tot:
        raise InvalidInput("IVA no cuadra")


def validar_iva_si_hay_total(
    neto_21,
    iva_21,
    neto_105,
    iva_105,
    neto_27,
    iva_27,
    no_gravado,
    percep_iva,
    percep_iibb,
    total,
) -> None:
    if total is None:
        return
    componentes = (
        neto_21,
        iva_21,
        neto_105,
        iva_105,
        neto_27,
        iva_27,
        no_gravado,
        percep_iva,
        percep_iibb,
    )
    if all(c is None for c in componentes):
        return
    validar_iva(
        neto_21,
        iva_21,
        neto_105,
        iva_105,
        neto_27,
        iva_27,
        no_gravado,
        percep_iva,
        percep_iibb,
        total,
    )


def validar_imputacion(obra: Obra | None, empresa_id: UUID) -> None:
    if obra is None:
        return
    if empresa_id not in obra.empresa_ids:
        raise InvalidInput("Empresa no participa en la obra")


def validar_afip_completo(
    tipo_afip: TipoAfip, cuit_emisor: str | None, punto_venta: int | None, numero: int | None
) -> ClaveAfip | None:
    clave = ClaveAfip.try_build(cuit_emisor, tipo_afip, punto_venta, numero)
    if tipo_afip in (TipoAfip.A, TipoAfip.B, TipoAfip.C) and clave is None:
        raise InvalidInput("Factura A/B/C exige CUIT emisor, punto de venta y número")
    return clave


def validar_editable(estado: EstadoPago) -> None:
    if estado != EstadoPago.PENDIENTE:
        raise InvalidInput("Editar/reemplazar archivo comprobado")


def validar_transicion(desde: EstadoPago, hacia: EstadoPago, actor: Usuario) -> None:
    if desde == EstadoPago.ANULADO:
        raise InvalidInput("Un anulado no cambia de estado")
    if hacia == EstadoPago.COMPROBADO_PAGADO:
        if desde != EstadoPago.PENDIENTE:
            raise InvalidInput("Solo un pendiente pasa a comprobado")
        return
    if hacia == EstadoPago.PENDIENTE:
        if desde != EstadoPago.COMPROBADO_PAGADO:
            raise InvalidInput("Solo se revierte un comprobado")
        if actor.rol != Rol.ADMIN:
            raise Forbidden("Solo el admin revierte un comprobado")
        return
    if hacia == EstadoPago.ANULADO:
        if desde == EstadoPago.COMPROBADO_PAGADO and actor.rol != Rol.ADMIN:
            raise Forbidden("Solo el admin anula un comprobado")
        return
    raise InvalidInput("Transición inválida")
