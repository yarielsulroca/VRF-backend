from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from vrf.application.use_cases.auth import Login
from vrf.application.use_cases.maestros import CrearEmpresa
from vrf.domain.entities import Empresa, Especialidad, RefreshToken, Usuario
from vrf.domain.enums import Rol
from vrf.domain.exceptions import Conflict, Unauthorized

GID = uuid4()
ESP_ID = uuid4()
CUIT_VRF = "33711174929"


class FakeUow:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class FakeGrupos:
    def get_unico(self) -> tuple:
        return GID, "VRF"


class FakeEspecialidades:
    def __init__(self) -> None:
        self.item = Especialidad(id=ESP_ID, grupo_id=GID, nombre="Generales", slug="generales")

    def get(self, id):
        return self.item if id == ESP_ID else None


class FakeEmpresas:
    def __init__(self) -> None:
        self.items: list[Empresa] = []

    def get_by_cuit(self, cuit: str) -> Empresa | None:
        return next((e for e in self.items if e.cuit == cuit), None)

    def add(self, item: Empresa) -> None:
        self.items.append(item)


class FakeUsuarios:
    def __init__(self, user: Usuario | None = None) -> None:
        self.user = user

    def get_by_email(self, email: str) -> Usuario | None:
        if self.user and self.user.email == email:
            return self.user
        return None


class FakeTokens:
    def __init__(self) -> None:
        self.items: list[RefreshToken] = []

    def add(self, item: RefreshToken) -> None:
        self.items.append(item)


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"h:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"h:{password}"


class FakeJwt:
    def emit_access(self, user_id, rol: str) -> str:
        return f"acc-{user_id}-{rol}"

    def emit_refresh(self) -> tuple[str, str, datetime]:
        return "raw-refresh", "hashed-refresh", datetime.now(timezone.utc) + timedelta(days=7)

    def hash_refresh(self, raw: str) -> str:
        return "hashed-refresh"


class FakeClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def _admin() -> Usuario:
    return Usuario(
        id=uuid4(),
        grupo_id=GID,
        email="admin@vrf.local",
        password_hash="h:secret",
        rol=Rol.ADMIN,
    )


def test_crear_empresa_ok() -> None:
    empresas = FakeEmpresas()
    uc = CrearEmpresa(empresas, FakeEspecialidades(), FakeGrupos(), FakeUow())
    creada = uc.execute(_admin(), "VRF S.A.", "33-71117492-9", ESP_ID)
    assert creada.cuit == CUIT_VRF
    assert len(empresas.items) == 1


def test_crear_empresa_cuit_duplicado() -> None:
    empresas = FakeEmpresas()
    empresas.items.append(
        Empresa(id=uuid4(), grupo_id=GID, razon_social="Ya", cuit=CUIT_VRF, especialidad_id=ESP_ID)
    )
    uc = CrearEmpresa(empresas, FakeEspecialidades(), FakeGrupos(), FakeUow())
    with pytest.raises(Conflict):
        uc.execute(_admin(), "Otra", "33-71117492-9", ESP_ID)


def test_login_invalido() -> None:
    uc = Login(FakeUsuarios(), FakeTokens(), FakeHasher(), FakeJwt(), FakeClock(), FakeUow())
    with pytest.raises(Unauthorized):
        uc.execute("nadie@vrf.local", "x")


def test_login_password_errada() -> None:
    user = _admin()
    uc = Login(FakeUsuarios(user), FakeTokens(), FakeHasher(), FakeJwt(), FakeClock(), FakeUow())
    with pytest.raises(Unauthorized):
        uc.execute(user.email, "otra")


def test_login_ok() -> None:
    user = _admin()
    tokens = FakeTokens()
    uc = Login(FakeUsuarios(user), tokens, FakeHasher(), FakeJwt(), FakeClock(), FakeUow())
    out = uc.execute(user.email, "secret")
    assert out["token_type"] == "bearer"
    assert out["rol"] == "admin"
    assert len(tokens.items) == 1
