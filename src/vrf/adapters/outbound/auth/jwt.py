import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from vrf.domain.exceptions import Unauthorized


class JwtTokens:
    def __init__(self, access_secret: str, refresh_secret: str) -> None:
        self._access = access_secret
        self._refresh = refresh_secret

    def emit_access(self, user_id: UUID, rol: str) -> str:
        payload = {
            "sub": str(user_id),
            "rol": rol,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        return jwt.encode(payload, self._access, algorithm="HS256")

    def emit_refresh(self) -> tuple[str, str, datetime]:
        raw = secrets.token_urlsafe(48)
        expira = datetime.now(timezone.utc) + timedelta(days=7)
        return raw, self.hash_refresh(raw), expira

    def parse_access(self, token: str) -> tuple[UUID, str]:
        try:
            data = jwt.decode(token, self._access, algorithms=["HS256"])
            return UUID(data["sub"]), data["rol"]
        except (jwt.PyJWTError, KeyError, ValueError) as exc:
            raise Unauthorized("Token inválido") from exc

    def hash_refresh(self, raw: str) -> str:
        return hashlib.sha256((raw + self._refresh).encode()).hexdigest()
