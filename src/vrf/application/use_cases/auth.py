from uuid import uuid4

from vrf.domain.entities import RefreshToken
from vrf.domain.exceptions import Unauthorized
from vrf.domain.ports.repositories import RefreshTokenRepository, UnitOfWork, UsuarioRepository
from vrf.domain.ports.security import Clock, PasswordHasher, TokenService


class Login:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        jwt: TokenService,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._usuarios = usuarios
        self._tokens = tokens
        self._hasher = hasher
        self._jwt = jwt
        self._clock = clock
        self._uow = uow

    def execute(self, email: str, password: str) -> dict:
        user = self._usuarios.get_by_email(email.strip().lower())
        if user is None or not user.activo or not self._hasher.verify(password, user.password_hash):
            raise Unauthorized("Credenciales inválidas")
        raw, hashed, expira = self._jwt.emit_refresh()
        self._tokens.add(
            RefreshToken(id=uuid4(), usuario_id=user.id, token_hash=hashed, expira=expira)
        )
        self._uow.commit()
        return {
            "access_token": self._jwt.emit_access(user.id, user.rol.value),
            "refresh_token": raw,
            "token_type": "bearer",
            "rol": user.rol.value,
            "usuario_id": str(user.id),
        }


class Refresh:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        tokens: RefreshTokenRepository,
        jwt: TokenService,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._usuarios = usuarios
        self._tokens = tokens
        self._jwt = jwt
        self._clock = clock
        self._uow = uow

    def execute(self, refresh_token: str) -> dict:
        hashed = self._jwt.hash_refresh(refresh_token)
        stored = self._tokens.get_by_hash(hashed)
        if stored is None or stored.revocado or stored.expira <= self._clock.now():
            raise Unauthorized("Refresh inválido")
        user = self._usuarios.get(stored.usuario_id)
        if user is None or not user.activo:
            raise Unauthorized("Usuario inactivo")
        return {
            "access_token": self._jwt.emit_access(user.id, user.rol.value),
            "token_type": "bearer",
        }


class Logout:
    def __init__(self, tokens: RefreshTokenRepository, jwt: TokenService, uow: UnitOfWork) -> None:
        self._tokens = tokens
        self._jwt = jwt
        self._uow = uow

    def execute(self, refresh_token: str) -> None:
        self._tokens.revoke(self._jwt.hash_refresh(refresh_token))
        self._uow.commit()
