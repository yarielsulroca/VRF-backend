from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from vrf.application.use_cases.comprobantes import CambiarEstado, CrearComprobante, DatosAlta, ServirOriginal
from vrf.application.use_cases.consultas import ConsultarCostosObra, ConsultarDashboard
from vrf.application.use_cases.maestros import CrearEspecialidad
from vrf.domain.entities import Archivo, Cliente, Comprobante, Empresa, Obra, Proveedor, Rubro, Usuario
from vrf.domain.enums import (
    AmbitoRubro,
    ClaseRubro,
    Clasificacion,
    EstadoObra,
    EstadoPago,
    Rol,
    TipoAfip,
    TipoTrabajo,
)
from vrf.domain.exceptions import Conflict, Forbidden, InvalidInput
from vrf.domain.ports.storage import StoredFile
from vrf.domain.vos import dinero

GID = uuid4()
E1 = uuid4()
E2 = uuid4()
OID = uuid4()
CID = uuid4()
RUBRO = uuid4()
PROV = uuid4()
ESP = uuid4()
CUIT = "33711174929"


class FakeUow:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class FakeClock:
    def now(self):
        return datetime(2026, 9, 5, tzinfo=timezone.utc)


class FakeStorage:
    def save(self, data, nombre, mime):
        return StoredFile(nombre, mime, "p", "abc", len(data))

    def read(self, path):
        return b"pdf-bytes"


class FakeGrupos:
    def get_unico(self):
        return GID, "VRF"


class FakeEspecialidades:
    def get_by_slug(self, grupo_id, slug: str):
        return None

    def add(self, item) -> None:
        return None


class FakeEmpresas:
    def __init__(self) -> None:
        self.items = {
            E1: Empresa(id=E1, grupo_id=GID, razon_social="VRF S.A.", cuit=CUIT, especialidad_id=ESP),
            E2: Empresa(
                id=E2, grupo_id=GID, razon_social="Eléctrica demo", cuit="30712345620", especialidad_id=ESP
            ),
        }

    def get(self, id):
        return self.items.get(id)


class FakeObras:
    def get(self, id):
        if id != OID:
            return None
        return Obra(
            id=OID,
            cliente_id=CID,
            nombre="Mostaza Rivadavia",
            direccion="Av. Rivadavia 64",
            tipo_trabajo=TipoTrabajo.INSTALACION,
            estado=EstadoObra.ABIERTA,
            empresa_ids=[E1, E2],
        )

    def list_by_grupo(self, grupo_id):
        item = self.get(OID)
        return [item] if item else []

    def list_by_cliente(self, cliente_id):
        return self.list_by_grupo(GID) if cliente_id == CID else []


class FakeClientes:
    def get(self, id):
        if id != CID:
            return None
        return Cliente(id=CID, grupo_id=GID, nombre="Mostaza", cuit=None)


class FakeProveedores:
    def get(self, id):
        if id != PROV:
            return None
        return Proveedor(id=PROV, grupo_id=GID, razon_social="Prov", cuit=CUIT)


class FakeRubros:
    def get(self, id):
        if id != RUBRO:
            return None
        return Rubro(
            id=RUBRO,
            empresa_id=E1,
            nombre="Cañería",
            clase=ClaseRubro.COMPRA_COSTO,
            ambito=AmbitoRubro.AMBOS,
        )


class FakeTipos:
    def get(self, id):
        return None


class FakeUsuarios:
    def get(self, id):
        return None


class FakeComps:
    def __init__(self) -> None:
        self.items: list[Comprobante] = []

    def add(self, item: Comprobante) -> None:
        self.items.append(item)

    def get(self, id):
        return next((c for c in self.items if c.id == id), None)

    def save(self, item: Comprobante) -> None:
        for i, actual in enumerate(self.items):
            if actual.id == item.id:
                self.items[i] = item
                return
        self.items.append(item)

    def get_by_clave_afip(self, cuit_emisor, tipo_afip, punto_venta, numero):
        return next(
            (
                c
                for c in self.items
                if c.cuit_emisor == cuit_emisor
                and c.tipo_afip.value == tipo_afip
                and c.punto_venta == punto_venta
                and c.numero == numero
            ),
            None,
        )

    def posible_duplicado_foto(self, sha256, proveedor_id, numero, fecha):
        return None

    def listar(
        self,
        empresa_id=None,
        obra_id=None,
        estado_pago=None,
        desde=None,
        hasta=None,
    ) -> list[Comprobante]:
        out = list(self.items)
        if empresa_id:
            out = [c for c in out if c.empresa_id == empresa_id]
        if obra_id:
            out = [c for c in out if c.obra_id == obra_id]
        if estado_pago:
            out = [c for c in out if c.estado_pago.value == estado_pago]
        if desde:
            out = [c for c in out if c.fecha >= desde]
        if hasta:
            out = [c for c in out if c.fecha <= hasta]
        return out


def _admin() -> Usuario:
    return Usuario(id=uuid4(), grupo_id=GID, email="admin@vrf.local", password_hash="h", rol=Rol.ADMIN)


def _op(empresa_ids=None) -> Usuario:
    return Usuario(
        id=uuid4(),
        grupo_id=GID,
        email="operativo@vrf.local",
        password_hash="h",
        rol=Rol.OPERATIVO,
        empresa_ids=empresa_ids if empresa_ids is not None else [E1],
    )


def _datos(**kwargs) -> DatosAlta:
    base = dict(
        empresa_id=E1,
        obra_id=OID,
        proveedor_id=PROV,
        clasificacion=Clasificacion.COMPRA,
        rubro_id=RUBRO,
        tipo_pago_id=None,
        tipo_afip=TipoAfip.A,
        punto_venta=1,
        numero=100,
        fecha=date(2026, 7, 15),
        neto_21=Decimal("100"),
        iva_21=Decimal("21"),
        neto_105=Decimal("0"),
        iva_105=Decimal("0"),
        neto_27=Decimal("0"),
        iva_27=Decimal("0"),
        no_gravado=Decimal("0"),
        percep_iva=Decimal("0"),
        percep_iibb=Decimal("0"),
        total=Decimal("121"),
        ya_pagada=False,
        nota=None,
        extra={},
        nombre_original="f.pdf",
        mime="application/pdf",
        contenido=b"pdf",
    )
    base.update(kwargs)
    return DatosAlta(**base)


def _crear(comps: FakeComps) -> CrearComprobante:
    return CrearComprobante(
        comps,
        FakeEmpresas(),
        FakeObras(),
        FakeProveedores(),
        FakeRubros(),
        FakeTipos(),
        FakeUsuarios(),
        FakeStorage(),
        FakeClock(),
        FakeUow(),
    )


def _dash(comps: FakeComps) -> ConsultarDashboard:
    return ConsultarDashboard(comps, FakeEmpresas(), FakeObras(), FakeProveedores(), FakeGrupos())


def _costos(comps: FakeComps) -> ConsultarCostosObra:
    return ConsultarCostosObra(
        comps, FakeObras(), FakeClientes(), FakeEmpresas(), FakeProveedores(), FakeRubros(), FakeTipos()
    )


def test_duplicado_afip_trae_link_al_existente() -> None:
    comps = FakeComps()
    uc = _crear(comps)
    admin = _admin()
    primero = uc.execute(admin, _datos())["comprobante"]
    with pytest.raises(Conflict) as err:
        uc.execute(admin, _datos())
    extra = err.value.extra
    assert extra["comprobanteId"] == str(primero.id)
    assert extra["empresaId"] == str(E1)
    assert extra["obraId"] == str(OID)


def test_pendiente_no_mueve_kpi_comprobado_suma_en_mes_de_fecha() -> None:
    comps = FakeComps()
    admin = _admin()
    creado = _crear(comps).execute(admin, _datos())["comprobante"]
    dash = _dash(comps).execute(admin, mes="2026-07")
    assert dash.total_comprobado == dinero(0)
    assert dash.total_pendientes == dinero("121.00")
    CambiarEstado(comps, FakeClock(), FakeUow()).execute(admin, creado.id, EstadoPago.COMPROBADO_PAGADO)
    julio = _dash(comps).execute(admin, mes="2026-07")
    sept = _dash(comps).execute(admin, mes="2026-09")
    assert julio.total_comprobado == dinero("121.00")
    assert sept.total_comprobado == dinero(0)


def test_dos_empresas_dos_columnas_absorbido() -> None:
    comps = FakeComps()
    admin = _admin()
    _crear(comps).execute(admin, _datos(ya_pagada=True, numero=1, total=Decimal("200"), neto_21=Decimal("200"), iva_21=Decimal("0")))
    comps.items[0].empresa_id = E1
    segundo = Comprobante(
        id=uuid4(),
        empresa_id=E2,
        obra_id=OID,
        proveedor_id=PROV,
        usuario_id=admin.id,
        clasificacion=Clasificacion.COMPRA,
        rubro_id=None,
        tipo_pago_id=None,
        tipo_afip=TipoAfip.C,
        punto_venta=1,
        numero=2,
        fecha=date(2026, 7, 15),
        neto_21=Decimal("80.00"),
        iva_21=Decimal("0.00"),
        neto_105=Decimal("0.00"),
        iva_105=Decimal("0.00"),
        neto_27=Decimal("0.00"),
        iva_27=Decimal("0.00"),
        no_gravado=Decimal("0.00"),
        percep_iva=Decimal("0.00"),
        percep_iibb=Decimal("0.00"),
        total=Decimal("80.00"),
        estado_pago=EstadoPago.COMPROBADO_PAGADO,
        cuit_emisor="30712345620",
    )
    comps.add(segundo)
    costos = _costos(comps).execute(admin, OID)
    assert [c.empresa_id for c in costos.empresas] == [E1, E2]
    assert costos.empresas[0].absorbido == dinero("200.00")
    assert costos.empresas[1].absorbido == dinero("80.00")
    assert costos.costo_grupo == dinero("280.00")


def test_operativo_no_revierte_comprobado() -> None:
    comps = FakeComps()
    admin = _admin()
    op = _op()
    creado = _crear(comps).execute(op, _datos(ya_pagada=True))["comprobante"]
    assert creado.estado_pago == EstadoPago.COMPROBADO_PAGADO
    with pytest.raises(Forbidden):
        CambiarEstado(comps, FakeClock(), FakeUow()).execute(op, creado.id, EstadoPago.PENDIENTE)
    with pytest.raises(Forbidden):
        CambiarEstado(comps, FakeClock(), FakeUow()).execute(op, creado.id, EstadoPago.ANULADO)
    CambiarEstado(comps, FakeClock(), FakeUow()).execute(admin, creado.id, EstadoPago.PENDIENTE)
    assert comps.get(creado.id).estado_pago == EstadoPago.PENDIENTE


def test_operativo_marca_pendiente_a_comprobado_y_no_edita_maestros() -> None:
    comps = FakeComps()
    op = _op()
    creado = _crear(comps).execute(op, _datos())["comprobante"]
    CambiarEstado(comps, FakeClock(), FakeUow()).execute(op, creado.id, EstadoPago.COMPROBADO_PAGADO)
    assert comps.get(creado.id).estado_pago == EstadoPago.COMPROBADO_PAGADO
    with pytest.raises(Forbidden):
        CrearEspecialidad(FakeEspecialidades(), FakeGrupos(), FakeUow()).execute(op, "X", "x")


def test_operativo_no_sirve_original_de_empresa_ajena() -> None:
    cid = uuid4()
    item = Comprobante(
        id=cid,
        empresa_id=E2,
        obra_id=OID,
        proveedor_id=PROV,
        usuario_id=uuid4(),
        clasificacion=Clasificacion.COMPRA,
        rubro_id=RUBRO,
        tipo_pago_id=None,
        tipo_afip=TipoAfip.A,
        punto_venta=1,
        numero=9,
        fecha=date(2026, 7, 1),
        neto_21=Decimal("10"),
        iva_21=Decimal("2.10"),
        neto_105=Decimal("0"),
        iva_105=Decimal("0"),
        neto_27=Decimal("0"),
        iva_27=Decimal("0"),
        no_gravado=Decimal("0"),
        percep_iva=Decimal("0"),
        percep_iibb=Decimal("0"),
        total=Decimal("12.10"),
        estado_pago=EstadoPago.PENDIENTE,
        cuit_emisor=CUIT,
        archivo=Archivo(id=uuid4(), comprobante_id=cid, nombre_original="f.pdf", mime="application/pdf", path="p", sha256="abc", size=3),
    )
    comps = FakeComps()
    comps.add(item)
    with pytest.raises(Forbidden):
        ServirOriginal(comps, FakeStorage()).execute(_op([E1]), cid)
    meta, data = ServirOriginal(comps, FakeStorage()).execute(_admin(), cid)
    assert meta.nombre_original == "f.pdf"
    assert data == b"pdf-bytes"


def test_alta_iva_desbalanceado_no_pasa() -> None:
    with pytest.raises(InvalidInput, match="IVA no cuadra"):
        _crear(FakeComps()).execute(_admin(), _datos(total=Decimal("999")))
