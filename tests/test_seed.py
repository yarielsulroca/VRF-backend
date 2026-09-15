from uuid import uuid4

from vrf.application.use_cases.seed import (
    CUIT_ELEC,
    CUIT_VRF,
    RUBROS_ELEC,
    RUBROS_VRF,
    TIPOS_PAGO,
    SeedInicial,
)
from vrf.domain.entities import Empresa, Especialidad, Rubro, TipoPago, Usuario
from vrf.domain.enums import Rol
from vrf.domain.vos import Cuit


class FakeUow:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class FakeGrupos:
    def __init__(self) -> None:
        self.id = uuid4()

    def ensure_seed_grupo(self, nombre: str, dueno: str):
        return self.id

    def get_unico(self):
        return self.id, "VRF"


class FakeEspecialidades:
    def __init__(self) -> None:
        self.items: list[Especialidad] = []

    def get_by_slug(self, grupo_id, slug: str) -> Especialidad | None:
        return next((e for e in self.items if e.grupo_id == grupo_id and e.slug == slug), None)

    def add(self, item: Especialidad) -> None:
        self.items.append(item)


class FakeEmpresas:
    def __init__(self) -> None:
        self.items: list[Empresa] = []

    def get_by_cuit(self, cuit: str) -> Empresa | None:
        return next((e for e in self.items if e.cuit == cuit), None)

    def add(self, item: Empresa) -> None:
        self.items.append(item)


class FakeUsuarios:
    def __init__(self) -> None:
        self.items: list[Usuario] = []

    def get_by_email(self, email: str) -> Usuario | None:
        return next((u for u in self.items if u.email == email), None)

    def add(self, item: Usuario) -> None:
        self.items.append(item)


class FakeRubros:
    def __init__(self) -> None:
        self.items: list[Rubro] = []

    def list_by_empresa(self, empresa_id) -> list[Rubro]:
        return [r for r in self.items if r.empresa_id == empresa_id]

    def add(self, item: Rubro) -> None:
        self.items.append(item)


class FakeTipos:
    def __init__(self) -> None:
        self.items: list[TipoPago] = []

    def list_by_empresa(self, empresa_id) -> list[TipoPago]:
        return [t for t in self.items if t.empresa_id == empresa_id]

    def add(self, item: TipoPago) -> None:
        self.items.append(item)


class FakeClientes:
    def __init__(self) -> None:
        self.items = []

    def get_by_nombre(self, grupo_id, nombre: str):
        return next((c for c in self.items if c.grupo_id == grupo_id and c.nombre == nombre), None)

    def add(self, item) -> None:
        self.items.append(item)


class FakeObras:
    def __init__(self) -> None:
        self.items = []

    def list_by_grupo(self, grupo_id):
        return list(self.items)

    def add(self, item) -> None:
        self.items.append(item)

    def save(self, item) -> None:
        for i, actual in enumerate(self.items):
            if actual.id == item.id:
                self.items[i] = item
                return


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"h:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"h:{password}"


def _seed():
    grupos = FakeGrupos()
    especialidades = FakeEspecialidades()
    empresas = FakeEmpresas()
    usuarios = FakeUsuarios()
    rubros = FakeRubros()
    tipos = FakeTipos()
    clientes = FakeClientes()
    obras = FakeObras()
    SeedInicial(
        grupos,
        especialidades,
        empresas,
        usuarios,
        rubros,
        tipos,
        clientes,
        obras,
        FakeHasher(),
        FakeUow(),
        admin_email="admin@vrf.local",
        admin_password="change-me",
        operativo_email="operativo@vrf.local",
        operativo_password="change-me",
    ).execute()
    return grupos, especialidades, empresas, usuarios, rubros, tipos, clientes, obras


def test_seed_vrf_completo() -> None:
    _grupos, especialidades, empresas, usuarios, rubros, tipos, clientes, obras = _seed()
    slugs = {e.slug for e in especialidades.items}
    assert slugs == {"climatizacion_generales", "instalacion_electrica"}
    vrf = empresas.get_by_cuit(Cuit(CUIT_VRF).value)
    elec = empresas.get_by_cuit(Cuit(CUIT_ELEC).value)
    assert vrf is not None and vrf.razon_social == "VRF S.A." and vrf.activa
    assert elec is not None and elec.razon_social == "Eléctrica demo"
    nombres_vrf = {r.nombre for r in rubros.list_by_empresa(vrf.id)}
    assert nombres_vrf == set(RUBROS_VRF)
    assert "Flete" not in nombres_vrf
    assert {r.nombre for r in rubros.list_by_empresa(elec.id)} == set(RUBROS_ELEC)
    nombres_tipo = {n for n, _ in TIPOS_PAGO}
    assert {t.nombre for t in tipos.list_by_empresa(vrf.id)} == nombres_tipo
    assert {t.nombre for t in tipos.list_by_empresa(elec.id)} == nombres_tipo
    admin = usuarios.get_by_email("admin@vrf.local")
    op = usuarios.get_by_email("operativo@vrf.local")
    assert admin is not None and admin.rol == Rol.ADMIN
    assert op is not None and op.rol == Rol.OPERATIVO
    assert op.empresa_ids == [vrf.id]
    assert clientes.get_by_nombre(_grupos.id, "Mostaza") is not None
    obra = next(o for o in obras.items if o.nombre == "Mostaza Rivadavia")
    assert set(obra.empresa_ids) == {vrf.id, elec.id}


def test_seed_es_idempotente() -> None:
    grupos = FakeGrupos()
    especialidades = FakeEspecialidades()
    empresas = FakeEmpresas()
    usuarios = FakeUsuarios()
    rubros = FakeRubros()
    tipos = FakeTipos()
    clientes = FakeClientes()
    obras = FakeObras()
    uc = SeedInicial(
        grupos,
        especialidades,
        empresas,
        usuarios,
        rubros,
        tipos,
        clientes,
        obras,
        FakeHasher(),
        FakeUow(),
        "admin@vrf.local",
        "change-me",
    )
    uc.execute()
    uc.execute()
    assert len(empresas.items) == 2
    assert len(usuarios.items) == 2
    assert len(especialidades.items) == 2
    assert len(obras.items) == 1
    assert len(clientes.items) == 1
    vrf = empresas.get_by_cuit(Cuit(CUIT_VRF).value)
    assert vrf is not None
    assert len(rubros.list_by_empresa(vrf.id)) == len(RUBROS_VRF)
    assert len(tipos.list_by_empresa(vrf.id)) == len(TIPOS_PAGO)
