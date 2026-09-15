import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vrf.adapters.inbound.api.handlers import register_handlers
from vrf.adapters.inbound.api.routers import auth, comprobantes, consultas, libro_iva, maestros, obras
from vrf.adapters.outbound.auth.hasher import BcryptHasher
from vrf.adapters.outbound.postgres.repos import (
    ClienteRepo,
    EmpresaRepo,
    EspecialidadRepo,
    GrupoRepo,
    ObraRepo,
    RubroRepo,
    TipoPagoRepo,
    UsuarioRepo,
)
from vrf.adapters.outbound.postgres.session import SessionLocal, SqlUnitOfWork
from vrf.application.use_cases.seed import SeedInicial
from vrf.config import settings

log = logging.getLogger("vrf")


def _seed() -> None:
    session = SessionLocal()
    try:
        SeedInicial(
            grupos=GrupoRepo(session),
            especialidades=EspecialidadRepo(session),
            empresas=EmpresaRepo(session),
            usuarios=UsuarioRepo(session),
            rubros=RubroRepo(session),
            tipos=TipoPagoRepo(session),
            clientes=ClienteRepo(session),
            obras=ObraRepo(session),
            hasher=BcryptHasher(),
            uow=SqlUnitOfWork(session),
            admin_email=settings.admin_email,
            admin_password=settings.admin_password,
            operativo_email=settings.operativo_email,
            operativo_password=settings.operativo_password,
        ).execute()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_app(*, seed_on_start: bool = True) -> FastAPI:
    settings.validate_runtime()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if seed_on_start:
            try:
                _seed()
            except Exception:
                log.exception("semilla inicial falló")
        yield

    kwargs: dict = {}
    if settings.is_production:
        kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

    app = FastAPI(title="VRF API", lifespan=lifespan, **kwargs)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_handlers(app)
    app.include_router(auth.router)
    app.include_router(maestros.router)
    app.include_router(obras.router)
    app.include_router(comprobantes.router)
    app.include_router(consultas.router)
    app.include_router(libro_iva.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
