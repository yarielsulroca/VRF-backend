from uuid import uuid4

import pytest

from vrf.domain.entities import Empresa, Obra
from vrf.domain.enums import EstadoObra, OrigenMantenimiento, TipoTrabajo
from vrf.domain.exceptions import InvalidInput
from vrf.domain.obra_reglas import validar_alta_obra, validar_quitar_participacion

GID = uuid4()
ESP = uuid4()
CLI = uuid4()
E1 = uuid4()
E2 = uuid4()


def _empresa(eid=E1) -> Empresa:
    return Empresa(id=eid, grupo_id=GID, razon_social="VRF", cuit="33711174929", especialidad_id=ESP)


def _obra_inst() -> Obra:
    return Obra(
        id=uuid4(),
        cliente_id=CLI,
        nombre="Instalacion",
        direccion="",
        tipo_trabajo=TipoTrabajo.INSTALACION,
        estado=EstadoObra.ABIERTA,
        empresa_ids=[E1],
    )


def test_instalacion_sin_empresas() -> None:
    with pytest.raises(InvalidInput):
        validar_alta_obra(
            TipoTrabajo.INSTALACION, None, None, CLI, None, None, [], [], GID
        )


def test_instalacion_ok() -> None:
    validar_alta_obra(
        TipoTrabajo.INSTALACION, None, None, CLI, None, None, [E1], [_empresa()], GID
    )


def test_instalacion_no_lleva_origen() -> None:
    with pytest.raises(InvalidInput):
        validar_alta_obra(
            TipoTrabajo.INSTALACION,
            OrigenMantenimiento.TERCEROS,
            None,
            CLI,
            "x",
            None,
            [E1],
            [_empresa()],
            GID,
        )


def test_mantenimiento_registrada() -> None:
    validar_alta_obra(
        TipoTrabajo.MANTENIMIENTO,
        OrigenMantenimiento.INSTALACION_REGISTRADA,
        _obra_inst(),
        CLI,
        None,
        None,
        [E1],
        [_empresa()],
        GID,
    )


def test_mantenimiento_registrada_otro_cliente() -> None:
    madre = _obra_inst()
    madre.cliente_id = uuid4()
    with pytest.raises(InvalidInput):
        validar_alta_obra(
            TipoTrabajo.MANTENIMIENTO,
            OrigenMantenimiento.INSTALACION_REGISTRADA,
            madre,
            CLI,
            None,
            None,
            [E1],
            [_empresa()],
            GID,
        )


def test_terceros_exige_nota() -> None:
    with pytest.raises(InvalidInput):
        validar_alta_obra(
            TipoTrabajo.MANTENIMIENTO,
            OrigenMantenimiento.TERCEROS,
            None,
            CLI,
            "  ",
            None,
            [E1],
            [_empresa()],
            GID,
        )


def test_sustitucion_exige_texto() -> None:
    with pytest.raises(InvalidInput):
        validar_alta_obra(
            TipoTrabajo.MANTENIMIENTO,
            OrigenMantenimiento.MANTENIMIENTO_SUSTITUCION,
            None,
            CLI,
            None,
            None,
            [E1],
            [_empresa()],
            GID,
        )


def test_empresa_otro_grupo() -> None:
    extra = _empresa(E2)
    extra.grupo_id = uuid4()
    with pytest.raises(InvalidInput):
        validar_alta_obra(
            TipoTrabajo.INSTALACION,
            None,
            None,
            CLI,
            None,
            None,
            [E2],
            [extra],
            GID,
        )


def test_no_quitar_ultima_ni_con_comprobantes() -> None:
    obra = _obra_inst()
    with pytest.raises(InvalidInput):
        validar_quitar_participacion(obra, E1, False)
    obra.empresa_ids = [E1, E2]
    with pytest.raises(InvalidInput):
        validar_quitar_participacion(obra, E1, True)
    validar_quitar_participacion(obra, E1, False)
