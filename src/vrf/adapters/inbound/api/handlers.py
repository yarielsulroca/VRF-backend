import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from vrf.domain.exceptions import Conflict, DomainError, Forbidden, NotFound, Unauthorized

log = logging.getLogger("vrf")


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        status = {
            Unauthorized: 401,
            Forbidden: 403,
            NotFound: 404,
            Conflict: 409,
        }.get(type(exc), 422)
        content = {"code": exc.code, "message": exc.message}
        extra = getattr(exc, "extra", None)
        if extra:
            content.update(extra)
        return JSONResponse(status_code=status, content=content)

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        log.exception("error interno")
        return JSONResponse(status_code=500, content={"code": "error", "message": "Error interno"})
