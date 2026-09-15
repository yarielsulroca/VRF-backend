from pydantic_settings import BaseSettings, SettingsConfigDict

_DEBILES = frozenset({"", "change-me", "changeme"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://vrf:vrf@localhost:5432/vrf"
    jwt_secret: str = "change-me"
    jwt_refresh_secret: str = "change-me"
    storage_path: str = "./storage"
    admin_email: str = "admin@vrf.local"
    admin_password: str = "change-me"
    operativo_email: str = "operativo@vrf.local"
    operativo_password: str = "change-me"
    cors_origins: str = "http://localhost:3000"
    vrf_env: str = "development"

    @property
    def is_production(self) -> bool:
        return self.vrf_env.strip().lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        out: list[str] = []
        for raw in self.cors_origins.split(","):
            origin = raw.strip()
            if origin and origin != "*":
                out.append(origin)
        return out

    def validate_runtime(self) -> None:
        if not self.is_production:
            return
        if self.jwt_secret.strip().lower() in _DEBILES:
            raise RuntimeError("JWT_SECRET no puede ser change-me en production")
        if self.jwt_refresh_secret.strip().lower() in _DEBILES:
            raise RuntimeError("JWT_REFRESH_SECRET no puede ser change-me en production")
        if self.admin_password.strip().lower() in _DEBILES:
            raise RuntimeError("ADMIN_PASSWORD no puede ser change-me en production")
        if "*" in {o.strip() for o in self.cors_origins.split(",")}:
            raise RuntimeError("CORS_ORIGINS no puede incluir * en production")
        if not self.cors_origin_list:
            raise RuntimeError("CORS_ORIGINS debe listar orígenes explícitos en production")


settings = Settings()
