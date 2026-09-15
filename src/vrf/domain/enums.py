from enum import StrEnum


class Rol(StrEnum):
    ADMIN = "admin"
    OPERATIVO = "operativo"


class TipoTrabajo(StrEnum):
    INSTALACION = "instalacion"
    MANTENIMIENTO = "mantenimiento"


class OrigenMantenimiento(StrEnum):
    INSTALACION_REGISTRADA = "instalacion_registrada"
    TERCEROS = "terceros"
    MANTENIMIENTO_SUSTITUCION = "mantenimiento_sustitucion"


class EstadoObra(StrEnum):
    ABIERTA = "abierta"
    CERRADA = "cerrada"


class ClaseRubro(StrEnum):
    COMPRA_COSTO = "compra_costo"
    AMBOS = "ambos"


class AmbitoRubro(StrEnum):
    INSTALACION = "instalacion"
    MANTENIMIENTO = "mantenimiento"
    AMBOS = "ambos"


class TipoAfip(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    X = "X"
    NINGUNO = "NINGUNO"


TIPOS_COMPROBANTE = (
    (TipoAfip.A, "Factura A"),
    (TipoAfip.B, "Factura B"),
    (TipoAfip.C, "Factura C"),
    (TipoAfip.X, "Comprobante no AFIP / foto"),
    (TipoAfip.NINGUNO, "Sin tipo AFIP"),
)


class Clasificacion(StrEnum):
    COMPRA = "compra"
    PAGO = "pago"
    COSTO = "costo"


class EstadoPago(StrEnum):
    PENDIENTE = "pendiente"
    COMPROBADO_PAGADO = "comprobado_pagado"
    ANULADO = "anulado"
