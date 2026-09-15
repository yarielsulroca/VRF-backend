import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from vrf.adapters.inbound.api.deps import current_user, exportar_libro_iva_uc
from vrf.adapters.inbound.api.serialize import dump
from vrf.application.use_cases.consultas import COLUMNAS_LIBRO_IVA, ExportarLibroIva, LibroIva
from vrf.domain.entities import Usuario

router = APIRouter(prefix="/libro-iva", tags=["libro-iva"])


def armar_csv(libro: LibroIva) -> str:
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNAS_LIBRO_IVA, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(libro.filas)
    return buffer.getvalue()


@router.get("")
def listar(
    empresa_id: UUID,
    mes: str,
    actor: Usuario = Depends(current_user),
    uc: ExportarLibroIva = Depends(exportar_libro_iva_uc),
) -> dict:
    return dump(uc.execute(actor, empresa_id, mes))


@router.get("/export")
def exportar(
    empresa_id: UUID,
    mes: str,
    actor: Usuario = Depends(current_user),
    uc: ExportarLibroIva = Depends(exportar_libro_iva_uc),
) -> Response:
    libro = uc.execute(actor, empresa_id, mes)
    return Response(
        content=armar_csv(libro),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="libro_iva_{mes}.csv"'},
    )
