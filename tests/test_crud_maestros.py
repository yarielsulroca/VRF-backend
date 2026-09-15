from uuid import uuid4

import pytest

from vrf.application.use_cases.maestros import (
    ActualizarEmpresa,
    ActualizarRubro,
    ListarTiposComprobante,
)
from vrf.application.use_cases.obras import ActualizarObra
from vrf.domain.entities import Empresa, Obra, Rubro, Usuario
from vrf.domain.enums import AmbitoRubro, ClaseRubro, EstadoObra, Rol, TipoTrabajo
from vrf.domain.exceptions import Conflict, Forbidden

GID = uuid4()
ESP_ID = uuid4()
CUIT_VRF = "33711174929"


class FakeUow:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class FakeEspecialidades:
    def get(self, id):
        from vrf.domain.entities import Especialidad

        if id != ESP_ID:
            return None
        return Especialidad(id=ESP_ID, grupo_id=GID, nombre="Generales", slug="generales")


class FakeEmpresas:
    def __init__(self) -> None:
        self.items: list[Empresa] = []

    def get(self, id):
        return next((e for e in self.items if e.id == id), None)

    def get_by_cuit(self, cuit: str) -> Empresa | None:
        return next((e for e in self.items if e.cuit == cuit), None)

    def save(self, item: Empresa) -> None:
        for i, actual in enumerate(self.items):
            if actual.id == item.id:
                self.items[i] = item
                return


class FakeRubros:
    def __init__(self) -> None:
        self.items: list[Rubro] = []

    def get(self, id):
        return next((r for r in self.items if r.id == id), None)

    def save(self, item: Rubro) -> None:
        for i, actual in enumerate(self.items):
            if actual.id == item.id:
                self.items[i] = item
                return


class FakeObras:
    def __init__(self) -> None:
        self.items: list[Obra] = []

    def get(self, id):
        return next((o for o in self.items if o.id == id), None)

    def save(self, item: Obra) -> None:
        for i, actual in enumerate(self.items):
            if actual.id == item.id:
                self.items[i] = item
                return


def _admin() -> Usuario:
    return Usuario(
        id=uuid4(), grupo_id=GID, email="admin@vrf.local", password_hash="h", rol=Rol.ADMIN
    )


def _operativo() -> Usuario:
    return Usuario(
        id=uuid4(),
        grupo_id=GID,
        email="op@vrf.local",
        password_hash="h",
        rol=Rol.OPERATIVO,
        empresa_ids=[uuid4()],
    )


def test_actualizar_empresa_ok() -> None:
    eid = uuid4()
    empresas = FakeEmpresas()
    empresas.items.append(
        Empresa(id=eid, grupo_id=GID, razon_social="VRF", cuit=CUIT_VRF, especialidad_id=ESP_ID)
    )
    uc = ActualizarEmpresa(empresas, FakeEspecialidades(), FakeUow())
    out = uc.execute(_admin(), eid, razon_social="VRF SA", activa=False)
    assert out.razon_social == "VRF SA"
    assert out.activa is False


def test_actualizar_empresa_cuit_duplicado() -> None:
    e1 = uuid4()
    e2 = uuid4()
    empresas = FakeEmpresas()
    empresas.items.extend(
        [
            Empresa(id=e1, grupo_id=GID, razon_social="A", cuit=CUIT_VRF, especialidad_id=ESP_ID),
            Empresa(id=e2, grupo_id=GID, razon_social="B", cuit="30712345620", especialidad_id=ESP_ID),
        ]
    )
    uc = ActualizarEmpresa(empresas, FakeEspecialidades(), FakeUow())
    with pytest.raises(Conflict):
        uc.execute(_admin(), e2, cuit="33-71117492-9")


def test_operativo_no_edita_empresa() -> None:
    eid = uuid4()
    empresas = FakeEmpresas()
    empresas.items.append(
        Empresa(id=eid, grupo_id=GID, razon_social="VRF", cuit=CUIT_VRF, especialidad_id=ESP_ID)
    )
    uc = ActualizarEmpresa(empresas, FakeEspecialidades(), FakeUow())
    with pytest.raises(Forbidden):
        uc.execute(_operativo(), eid, activa=False)


def test_desactivar_rubro() -> None:
    rid = uuid4()
    rubros = FakeRubros()
    rubros.items.append(
        Rubro(
            id=rid,
            empresa_id=uuid4(),
            nombre="Cañería",
            clase=ClaseRubro.COMPRA_COSTO,
            ambito=AmbitoRubro.AMBOS,
        )
    )
    uc = ActualizarRubro(rubros, FakeUow())
    out = uc.execute(_admin(), rid, activo=False)
    assert out.activo is False


def test_actualizar_obra_no_toca_origen() -> None:
    oid = uuid4()
    obras = FakeObras()
    obras.items.append(
        Obra(
            id=oid,
            cliente_id=uuid4(),
            nombre="Obra",
            direccion="",
            tipo_trabajo=TipoTrabajo.INSTALACION,
            estado=EstadoObra.ABIERTA,
            empresa_ids=[uuid4()],
        )
    )
    uc = ActualizarObra(obras, FakeUow())
    out = uc.execute(_admin(), oid, nombre="Obra 2", estado=EstadoObra.CERRADA)
    assert out.nombre == "Obra 2"
    assert out.estado == EstadoObra.CERRADA
    assert out.tipo_trabajo == TipoTrabajo.INSTALACION
    assert out.origen_mantenimiento is None


def test_tipos_comprobante_catalogo_cerrado() -> None:
    filas = ListarTiposComprobante().execute()
    codigos = {f["codigo"] for f in filas}
    assert codigos == {"A", "B", "C", "X", "NINGUNO"}
