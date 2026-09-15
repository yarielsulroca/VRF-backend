from decimal import Decimal
from uuid import uuid4

import pytest

from vrf.domain.comprobante_reglas import (
    validar_clasificacion,
    validar_editable,
    validar_imputacion,
    validar_iva,
    validar_transicion,
)
from vrf.domain.entities import Obra, Usuario
from vrf.domain.enums import Clasificacion, EstadoObra, EstadoPago, Rol, TipoTrabajo
from vrf.domain.exceptions import Forbidden, InvalidInput

GID = uuid4()
E1 = uuid4()


def _admin() -> Usuario:
    return Usuario(id=uuid4(), grupo_id=GID, email="a@x", password_hash="h", rol=Rol.ADMIN)


def _op() -> Usuario:
    return Usuario(
        id=uuid4(), grupo_id=GID, email="o@x", password_hash="h", rol=Rol.OPERATIVO, empresa_ids=[E1]
    )


def test_compra_exige_rubro() -> None:
    with pytest.raises(InvalidInput):
        validar_clasificacion(Clasificacion.COMPRA, None, None)


def test_pago_no_lleva_rubro() -> None:
    with pytest.raises(InvalidInput):
        validar_clasificacion(Clasificacion.PAGO, uuid4(), uuid4())
    validar_clasificacion(Clasificacion.PAGO, None, uuid4())


def test_iva_no_cuadra() -> None:
    with pytest.raises(InvalidInput):
        validar_iva(100, 21, 0, 0, 0, 0, 0, 0, 0, 100)


def test_iva_cuadra() -> None:
    validar_iva(100, 21, 0, 0, 0, 0, 0, 0, 0, 121)
    validar_iva(0, 0, 0, 0, 0, 0, 0, 0, 0, Decimal("50.00"))
    validar_iva(100, 21, 50, Decimal("5.25"), 10, Decimal("2.70"), 3, 4, 6, Decimal("201.95"))


def test_iva_percepciones_no_cuadran() -> None:
    with pytest.raises(InvalidInput, match="IVA no cuadra"):
        validar_iva(100, 21, 0, 0, 0, 0, 0, 0, 10, 121)


def test_empresa_no_participa() -> None:
    obra = Obra(
        id=uuid4(),
        cliente_id=uuid4(),
        nombre="o",
        direccion="",
        tipo_trabajo=TipoTrabajo.INSTALACION,
        estado=EstadoObra.ABIERTA,
        empresa_ids=[E1],
    )
    with pytest.raises(InvalidInput):
        validar_imputacion(obra, uuid4())
    validar_imputacion(obra, E1)
    validar_imputacion(None, E1)


def test_no_editar_comprobado() -> None:
    with pytest.raises(InvalidInput):
        validar_editable(EstadoPago.COMPROBADO_PAGADO)
    validar_editable(EstadoPago.PENDIENTE)


def test_operativo_no_revierte() -> None:
    with pytest.raises(Forbidden):
        validar_transicion(EstadoPago.COMPROBADO_PAGADO, EstadoPago.PENDIENTE, _op())
    validar_transicion(EstadoPago.COMPROBADO_PAGADO, EstadoPago.PENDIENTE, _admin())


def test_operativo_anula_pendiente_no_comprobado() -> None:
    validar_transicion(EstadoPago.PENDIENTE, EstadoPago.ANULADO, _op())
    with pytest.raises(Forbidden):
        validar_transicion(EstadoPago.COMPROBADO_PAGADO, EstadoPago.ANULADO, _op())
