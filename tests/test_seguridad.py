import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vrf.adapters.inbound.api.handlers import register_handlers
from vrf.adapters.outbound.auth.jwt import JwtTokens
from vrf.config import Settings
from vrf.domain.exceptions import Unauthorized
from vrf.main import create_app


def test_health_sin_auth() -> None:
    with TestClient(create_app(seed_on_start=False)) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_cors_origenes_explicitos_sin_wildcard() -> None:
    s = Settings(cors_origins=" http://localhost:3000 , * , http://127.0.0.1:3000 ")
    assert s.cors_origin_list == ["http://localhost:3000", "http://127.0.0.1:3000"]
    with TestClient(create_app(seed_on_start=False)) as client:
        r = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_500_sin_traceback() -> None:
    app = FastAPI()
    register_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secreto interno")

    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body == {"code": "error", "message": "Error interno"}
    assert "secreto" not in r.text
    assert "Traceback" not in r.text


def test_production_rechaza_secretos_debiles() -> None:
    s = Settings(vrf_env="production", jwt_secret="change-me", jwt_refresh_secret="fuerte", admin_password="fuerte")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        s.validate_runtime()
    s = Settings(
        vrf_env="production",
        jwt_secret="fuerte",
        jwt_refresh_secret="fuerte",
        admin_password="change-me",
    )
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        s.validate_runtime()
    s = Settings(
        vrf_env="production",
        jwt_secret="fuerte",
        jwt_refresh_secret="fuerte",
        admin_password="fuerte",
        cors_origins="*",
    )
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        s.validate_runtime()


def test_docs_off_en_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from vrf import config as cfg
    from vrf import main as mainmod

    monkeypatch.setattr(
        cfg.settings,
        "vrf_env",
        "production",
    )
    monkeypatch.setattr(cfg.settings, "jwt_secret", "prod-access-secret")
    monkeypatch.setattr(cfg.settings, "jwt_refresh_secret", "prod-refresh-secret")
    monkeypatch.setattr(cfg.settings, "admin_password", "prod-admin")
    monkeypatch.setattr(cfg.settings, "cors_origins", "https://vrf.example")
    monkeypatch.setattr(mainmod, "settings", cfg.settings)
    app = create_app(seed_on_start=False)
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/health").status_code == 200


def test_jwt_invalido() -> None:
    tokens = JwtTokens("access", "refresh")
    with pytest.raises(Unauthorized):
        tokens.parse_access("no-es-un-jwt")
    raw, hashed, _exp = tokens.emit_refresh()
    assert hashed != raw
    assert tokens.hash_refresh(raw) == hashed
