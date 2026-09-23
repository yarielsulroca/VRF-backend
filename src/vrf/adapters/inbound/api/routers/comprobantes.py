from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from vrf.adapters.inbound.api.deps import (
    actualizar_comprobante_uc,
    cambiar_estado_uc,
    confirmar_importacion_uc,
    crear_comprobante_uc,
    current_user,
    exportar_registros_uc,
    listar_comprobantes_uc,
    obtener_comprobante_uc,
    preview_ocr_uc,
    previa_importacion_uc,
    reemplazar_archivo_uc,
    servir_original_uc,
)
from vrf.adapters.inbound.api.schemas import ComprobanteAltaIn, ComprobantePatch, ImportarConfirmarIn
from vrf.adapters.inbound.api.serialize import dump
from vrf.application.use_cases.comprobantes import (
    ActualizarComprobante,
    CambiarEstado,
    CrearComprobante,
    DatosAlta,
    ListarComprobantes,
    ObtenerComprobante,
    ReemplazarArchivo,
    ServirOriginal,
)
from vrf.application.use_cases.ocr import PreviewOcr
from vrf.application.use_cases.planilla import ConfirmarImportacion, ExportarRegistros, PreviaImportacion
from vrf.domain.entities import Usuario
from vrf.domain.enums import Clasificacion, EstadoPago, TipoAfip
from vrf.domain.exceptions import InvalidInput

router = APIRouter(prefix="/comprobantes", tags=["comprobantes"])


@router.get("")
def listar(
    empresa_id: UUID | None = None,
    obra_id: UUID | None = None,
    estado_pago: str | None = None,
    cliente_id: UUID | None = None,
    proveedor_id: UUID | None = None,
    clasificacion: str | None = None,
    rubro_id: UUID | None = None,
    tipo_pago_id: UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    limit: int = 500,
    offset: int = 0,
    actor: Usuario = Depends(current_user),
    uc: ListarComprobantes = Depends(listar_comprobantes_uc),
) -> list:
    return [
        dump(x)
        for x in uc.execute(
            actor,
            empresa_id=empresa_id,
            obra_id=obra_id,
            estado_pago=estado_pago,
            cliente_id=cliente_id,
            proveedor_id=proveedor_id,
            clasificacion=clasificacion,
            rubro_id=rubro_id,
            tipo_pago_id=tipo_pago_id,
            desde=desde,
            hasta=hasta,
            q=q,
            limit=limit,
            offset=offset,
        )
    ]


@router.post("/ocr-preview")
async def ocr_preview(
    archivo: UploadFile = File(...),
    actor: Usuario = Depends(current_user),
    uc: PreviewOcr = Depends(preview_ocr_uc),
) -> dict:
    contenido = await archivo.read()
    mime = archivo.content_type or "application/octet-stream"
    return await run_in_threadpool(uc.execute, actor, contenido, mime)


@router.get("/exportar")
def exportar(
    columnas: str = "",
    empresa_id: UUID | None = None,
    obra_id: UUID | None = None,
    estado_pago: str | None = None,
    cliente_id: UUID | None = None,
    proveedor_id: UUID | None = None,
    clasificacion: str | None = None,
    rubro_id: UUID | None = None,
    tipo_pago_id: UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    actor: Usuario = Depends(current_user),
    uc: ExportarRegistros = Depends(exportar_registros_uc),
) -> Response:
    encabezados = [c.strip() for c in columnas.split(",") if c.strip()]
    data = uc.execute(
        actor,
        encabezados,
        empresa_id=empresa_id,
        obra_id=obra_id,
        estado_pago=estado_pago,
        cliente_id=cliente_id,
        proveedor_id=proveedor_id,
        clasificacion=clasificacion,
        rubro_id=rubro_id,
        tipo_pago_id=tipo_pago_id,
        desde=desde,
        hasta=hasta,
        q=q,
    )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="registros.xlsx"'},
    )


@router.post("/importar/previa")
async def importar_previa(
    archivo: UploadFile = File(...),
    empresa_id: UUID | None = None,
    clasificacion: str | None = None,
    actor: Usuario = Depends(current_user),
    uc: PreviaImportacion = Depends(previa_importacion_uc),
) -> dict:
    if empresa_id is None:
        raise InvalidInput("empresa_id es obligatorio para importar")
    contenido = await archivo.read()
    out = uc.execute(actor, contenido, empresa_id, clasificacion)
    out.pop("_filas", None)
    return out


@router.post("/importar/confirmar")
def importar_confirmar(
    body: ImportarConfirmarIn,
    actor: Usuario = Depends(current_user),
    uc: ConfirmarImportacion = Depends(confirmar_importacion_uc),
) -> dict:
    return uc.execute(actor, body.token)


@router.get("/{comprobante_id}")
def obtener(
    comprobante_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ObtenerComprobante = Depends(obtener_comprobante_uc),
) -> dict:
    return dump(uc.execute(actor, comprobante_id))


@router.post("")
async def crear(
    datos: str = Form(...),
    archivo: UploadFile | None = File(None),
    actor: Usuario = Depends(current_user),
    uc: CrearComprobante = Depends(crear_comprobante_uc),
) -> dict:
    body = ComprobanteAltaIn.model_validate_json(datos)
    contenido = await archivo.read() if archivo is not None else None
    mime = (archivo.content_type if archivo else None) or "application/octet-stream"
    nombre = (archivo.filename if archivo else None) or "sin_archivo"
    out = uc.execute(
        actor,
        DatosAlta(
            empresa_id=body.empresa_id,
            obra_id=body.obra_id,
            proveedor_id=body.proveedor_id,
            clasificacion=Clasificacion(body.clasificacion),
            rubro_id=body.rubro_id,
            tipo_pago_id=body.tipo_pago_id,
            tipo_afip=TipoAfip(body.tipo_afip),
            punto_venta=body.punto_venta,
            numero=body.numero,
            fecha=body.fecha,
            neto_21=body.neto_21,
            iva_21=body.iva_21,
            neto_105=body.neto_105,
            iva_105=body.iva_105,
            neto_27=body.neto_27,
            iva_27=body.iva_27,
            no_gravado=body.no_gravado,
            percep_iva=body.percep_iva,
            percep_iibb=body.percep_iibb,
            total=body.total,
            ya_pagada=body.ya_pagada,
            nota=body.nota,
            extra=body.extra,
            nombre_original=nombre,
            mime=mime,
            contenido=contenido,
            numero_comprobante=body.numero_comprobante,
        ),
    )
    payload = dump(out["comprobante"])
    payload["posible_duplicado_id"] = out["posible_duplicado_id"]
    return payload


@router.patch("/{comprobante_id}")
def patch_comprobante(
    comprobante_id: UUID,
    body: ComprobantePatch,
    actor: Usuario = Depends(current_user),
    uc: ActualizarComprobante = Depends(actualizar_comprobante_uc),
) -> dict:
    return dump(
        uc.execute(
            actor,
            comprobante_id,
            obra_id=body.obra_id,
            rubro_id=body.rubro_id,
            tipo_pago_id=body.tipo_pago_id,
            clasificacion=Clasificacion(body.clasificacion) if body.clasificacion else None,
            clear_obra=body.clear_obra,
        )
    )


@router.put("/{comprobante_id}/archivo")
async def reemplazar(
    comprobante_id: UUID,
    archivo: UploadFile = File(...),
    actor: Usuario = Depends(current_user),
    uc: ReemplazarArchivo = Depends(reemplazar_archivo_uc),
) -> dict:
    contenido = await archivo.read()
    return dump(
        uc.execute(
            actor,
            comprobante_id,
            contenido,
            archivo.filename or "archivo",
            archivo.content_type or "application/octet-stream",
        )
    )


@router.post("/{comprobante_id}/comprobar")
def comprobar(
    comprobante_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: CambiarEstado = Depends(cambiar_estado_uc),
) -> dict:
    return dump(uc.execute(actor, comprobante_id, EstadoPago.COMPROBADO_PAGADO))


@router.post("/{comprobante_id}/revertir")
def revertir(
    comprobante_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: CambiarEstado = Depends(cambiar_estado_uc),
) -> dict:
    return dump(uc.execute(actor, comprobante_id, EstadoPago.PENDIENTE))


@router.post("/{comprobante_id}/anular")
def anular(
    comprobante_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: CambiarEstado = Depends(cambiar_estado_uc),
) -> dict:
    return dump(uc.execute(actor, comprobante_id, EstadoPago.ANULADO))


@router.get("/{comprobante_id}/archivo")
def original(
    comprobante_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ServirOriginal = Depends(servir_original_uc),
) -> Response:
    meta, data = uc.execute(actor, comprobante_id)
    return Response(
        content=data,
        media_type=meta.mime,
        headers={"Content-Disposition": f'attachment; filename="{meta.nombre_original}"'},
    )
