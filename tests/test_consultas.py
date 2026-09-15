from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from vrf.adapters.inbound.api.routers.libro_iva import armar_csv
from vrf.application.use_cases.consultas import (
    COLUMNAS_LIBRO_IVA,
    ConsultarCostosObra,
    ConsultarDashboard,
    ExportarLibroIva,
    ListarCostos,
)
from vrf.domain.entities import Cliente, Comprobante, Empresa, Obra, Proveedor, Rubro, TipoPago, Usuario
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
from vrf.domain.exceptions import Forbidden
from vrf.domain.vos import dinero

GID = uuid4()
E1 = uuid4()
E2 = uuid4()
CID = uuid4()
OID = uuid4()
RID = uuid4()
TID = uuid4()
PID = uuid4()
ESP = uuid4()


def _admin() -> Usuario:
    return Usuario(id=uuid4(), grupo_id=GID, email="a@x", password_hash="h", rol=Rol.ADMIN)


def _op() -> Usuario:
    return Usuario(
        id=uuid4(),
        grupo_id=GID,
        email="o@x",
        password_hash="h",
        rol=Rol.OPERATIVO,
        empresa_ids=[E1],
    )


def _comp(**kwargs) -> Comprobante:
    base = dict(
        id=uuid4(),
        empresa_id=E1,
        obra_id=OID,
        proveedor_id=PID,
        usuario_id=uuid4(),
        clasificacion=Clasificacion.COMPRA,
        rubro_id=RID,
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
        comprobado_en=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    base.update(kwargs)
    return Comprobante(**base)


class FakeComps:
    def __init__(self, items: list[Comprobante]) -> None:
        self.items = items

    def listar(
        self,
        empresa_id=None,
        obra_id=None,
        estado_pago=None,
        desde=None,
        hasta=None,
    ) -> list[Comprobante]:
        out = self.items
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
        return list(out)


class FakeEmpresas:
    def __init__(self) -> None:
        self.items = {
            E1: Empresa(id=E1, grupo_id=GID, razon_social="VRF S.A.", cuit="33711174929", especialidad_id=ESP),
            E2: Empresa(id=E2, grupo_id=GID, razon_social="Eléctrica", cuit="30712345620", especialidad_id=ESP),
        }

    def get(self, id: UUID) -> Empresa | None:
        return self.items.get(id)


class FakeObras:
    def __init__(self) -> None:
        self.item = Obra(
            id=OID,
            cliente_id=CID,
            nombre="Mostaza Rivadavia",
            direccion="Av. Rivadavia 64",
            tipo_trabajo=TipoTrabajo.INSTALACION,
            estado=EstadoObra.ABIERTA,
            empresa_ids=[E1, E2],
        )

    def get(self, id: UUID) -> Obra | None:
        return self.item if id == OID else None

    def list_by_grupo(self, grupo_id: UUID) -> list[Obra]:
        return [self.item]

    def list_by_cliente(self, cliente_id: UUID) -> list[Obra]:
        return [self.item] if cliente_id == CID else []


class FakeClientes:
    def get(self, id: UUID) -> Cliente | None:
        if id != CID:
            return None
        return Cliente(id=CID, grupo_id=GID, nombre="Mostaza", cuit=None)


class FakeProveedores:
    def get(self, id: UUID) -> Proveedor | None:
        if id != PID:
            return None
        return Proveedor(id=PID, grupo_id=GID, razon_social="Ferretería", cuit="33711174929")


class FakeRubros:
    def get(self, id: UUID) -> Rubro | None:
        if id != RID:
            return None
        return Rubro(
            id=RID,
            empresa_id=E1,
            nombre="Cañería",
            clase=ClaseRubro.COMPRA_COSTO,
            ambito=AmbitoRubro.AMBOS,
        )


class FakeTipos:
    def get(self, id: UUID) -> TipoPago | None:
        if id != TID:
            return None
        return TipoPago(id=TID, empresa_id=E1, nombre="Flete", schema_extra={})


class FakeGrupos:
    def get_unico(self) -> tuple[UUID, str]:
        return GID, "VRF"


def _dash(items: list[Comprobante]) -> ConsultarDashboard:
    return ConsultarDashboard(FakeComps(items), FakeEmpresas(), FakeObras(), FakeProveedores(), FakeGrupos())


def _costos(items: list[Comprobante]) -> ConsultarCostosObra:
    return ConsultarCostosObra(
        FakeComps(items),
        FakeObras(),
        FakeClientes(),
        FakeEmpresas(),
        FakeProveedores(),
        FakeRubros(),
        FakeTipos(),
    )


def _libro(items: list[Comprobante]) -> ExportarLibroIva:
    return ExportarLibroIva(
        FakeComps(items),
        FakeEmpresas(),
        FakeObras(),
        FakeProveedores(),
        FakeRubros(),
        FakeTipos(),
    )


def test_pendiente_no_mueve_dashboard() -> None:
    dash = _dash([_comp(estado_pago=EstadoPago.PENDIENTE)]).execute(_admin(), mes="2026-07")
    assert dash.total_comprobado == dinero(0)
    assert dash.total_pendientes == dinero("121.00")
    assert len(dash.pendientes) == 1


def test_comprobado_suma_en_mes_de_fecha_no_de_auditoria() -> None:
    item = _comp(fecha=date(2026, 7, 31), comprobado_en=datetime(2026, 9, 5, tzinfo=timezone.utc))
    julio = _dash([item]).execute(_admin(), mes="2026-07")
    sept = _dash([item]).execute(_admin(), mes="2026-09")
    assert julio.total_comprobado == dinero("121.00")
    assert sept.total_comprobado == dinero(0)


def test_gasto_sin_obra_resta_empresa_no_compensa() -> None:
    gasto = _comp(obra_id=None, total=Decimal("50.00"), neto_21=Decimal("50.00"), iva_21=Decimal("0.00"))
    obra = _comp(total=Decimal("121.00"))
    dash = _dash([gasto, obra]).execute(_admin(), mes="2026-07")
    assert dash.total_comprobado == dinero("171.00")
    costos = _costos([gasto, obra]).execute(_admin(), OID)
    assert costos.costo_grupo == dinero("121.00")
    vrf = next(c for c in costos.empresas if c.empresa_id == E1)
    assert vrf.absorbido == dinero("121.00")


def test_dos_empresas_dos_columnas_absorbido() -> None:
    c1 = _comp(empresa_id=E1, numero=1, total=Decimal("200.00"), neto_21=Decimal("200.00"), iva_21=Decimal("0.00"))
    c2 = _comp(empresa_id=E2, numero=2, total=Decimal("80.00"), neto_21=Decimal("80.00"), iva_21=Decimal("0.00"))
    costos = _costos([c1, c2]).execute(_admin(), OID)
    assert [c.empresa_id for c in costos.empresas] == [E1, E2]
    assert costos.empresas[0].absorbido == dinero("200.00")
    assert costos.empresas[1].absorbido == dinero("80.00")
    assert costos.costo_grupo == dinero("280.00")


def test_operativo_no_ve_importes_ajenos() -> None:
    c1 = _comp(empresa_id=E1, numero=1)
    c2 = _comp(empresa_id=E2, numero=2, total=Decimal("999.00"))
    costos = _costos([c1, c2]).execute(_op(), OID)
    assert [c.empresa_id for c in costos.empresas] == [E1]
    assert costos.costo_grupo == dinero("121.00")
    dash = _dash([c1, c2]).execute(_op(), mes="2026-07")
    assert dash.total_comprobado == dinero("121.00")
    assert all(e.empresa_id == E1 for e in dash.por_empresa)
    with pytest.raises(Forbidden):
        _dash([c1, c2]).execute(_op(), mes="2026-07", empresa_id=E2)


def test_pago_agrupa_por_tipo() -> None:
    pago = _comp(
        clasificacion=Clasificacion.PAGO,
        rubro_id=None,
        tipo_pago_id=TID,
        total=Decimal("40.00"),
        neto_21=Decimal("40.00"),
        iva_21=Decimal("0.00"),
    )
    costos = _costos([pago]).execute(_admin(), OID)
    vrf = next(c for c in costos.empresas if c.empresa_id == E1)
    assert vrf.pagos_por_tipo[0].nombre == "Flete"
    assert vrf.pagos_por_tipo[0].total == dinero("40.00")


def test_libro_iva_incluye_pendiente_excluye_anulado_y_x() -> None:
    pend = _comp(estado_pago=EstadoPago.PENDIENTE, numero=10, tipo_afip=TipoAfip.A)
    anu = _comp(estado_pago=EstadoPago.ANULADO, numero=11, tipo_afip=TipoAfip.A)
    foto = _comp(tipo_afip=TipoAfip.X, numero=12, punto_venta=None)
    ok = _comp(numero=13, tipo_afip=TipoAfip.C)
    libro = _libro([pend, anu, foto, ok]).execute(_admin(), E1, "2026-07")
    numeros = {f["Número"] for f in libro.filas}
    assert "00000010" in numeros
    assert "00000013" in numeros
    assert "00000011" not in numeros
    assert "00000012" not in numeros
    estados = {f["Número"]: f["Estado"] for f in libro.filas}
    assert estados["00000010"] == "pendiente"
    assert estados["00000013"] == "comprobado_pagado"
    for col in ("IVA 21%", "Obra", "Rubro/Tipo", "Estado", "Percepción IIBB"):
        assert col in COLUMNAS_LIBRO_IVA
        assert col in libro.filas[0]
    csv_txt = armar_csv(libro)
    assert "pendiente" in csv_txt
    assert "comprobado_pagado" in csv_txt
    assert "anulado" not in csv_txt


def test_listar_costos_cliente() -> None:
    uc = ListarCostos(FakeComps([_comp()]), FakeObras(), FakeClientes(), FakeEmpresas(), FakeGrupos())
    out = uc.execute(_admin(), CID)
    assert out.cliente_nombre == "Mostaza"
    assert out.obras[0].costo_grupo == dinero("121.00")
    assert len(out.obras[0].por_empresa) == 2
