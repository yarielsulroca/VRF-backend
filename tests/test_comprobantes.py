from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from vrf.application.use_cases.comprobantes import CrearComprobante, DatosAlta
from vrf.domain.entities import Empresa, Proveedor, Rubro, Usuario
from vrf.domain.enums import AmbitoRubro, ClaseRubro, Clasificacion, Rol, TipoAfip
from vrf.domain.exceptions import Conflict, Forbidden, InvalidInput
from vrf.domain.ports.storage import StoredFile

GID = uuid4()
EID = uuid4()
RUBRO = uuid4()
PROV = uuid4()
CUIT = "33711174929"


class FakeUow:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class FakeClock:
    def now(self):
        return datetime.now(timezone.utc)


class FakeStorage:
    def save(self, data, nombre, mime):
        return StoredFile(nombre, mime, "p", "abc", len(data))

    def read(self, path):
        return b"x"


class FakeEmpresas:
    def get(self, id):
        if id != EID:
            return None
        return Empresa(id=EID, grupo_id=GID, razon_social="VRF", cuit=CUIT, especialidad_id=uuid4())


class FakeObras:
    def get(self, id):
        return None


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
            empresa_id=EID,
            nombre="Caños",
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
        self.items = []

    def add(self, item):
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


def _admin() -> Usuario:
    return Usuario(id=uuid4(), grupo_id=GID, email="admin@vrf.local", password_hash="h", rol=Rol.ADMIN)


def _datos(**kwargs) -> DatosAlta:
    base = dict(
        empresa_id=EID,
        obra_id=None,
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


def _uc(comps=None):
    return CrearComprobante(
        comps or FakeComps(),
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


def test_alta_pendiente() -> None:
    comps = FakeComps()
    out = _uc(comps).execute(_admin(), _datos())
    assert out["comprobante"].estado_pago.value == "pendiente"
    assert len(comps.items) == 1


def test_ya_pagada_comprobado() -> None:
    out = _uc().execute(_admin(), _datos(ya_pagada=True))
    assert out["comprobante"].estado_pago.value == "comprobado_pagado"


def test_duplicado_afip() -> None:
    comps = FakeComps()
    uc = _uc(comps)
    uc.execute(_admin(), _datos())
    with pytest.raises(Conflict) as err:
        uc.execute(_admin(), _datos())
    assert err.value.extra["empresaId"] == str(EID)


def test_alta_iva_no_cuadra() -> None:
    with pytest.raises(InvalidInput, match="IVA no cuadra"):
        _uc().execute(_admin(), _datos(total=Decimal("100")))


def test_operativo_empresa_ajena() -> None:
    op = Usuario(
        id=uuid4(),
        grupo_id=GID,
        email="op@x",
        password_hash="h",
        rol=Rol.OPERATIVO,
        empresa_ids=[uuid4()],
    )
    with pytest.raises(Forbidden):
        _uc().execute(op, _datos())
