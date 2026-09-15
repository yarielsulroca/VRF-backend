from uuid import UUID

from fastapi import APIRouter, Depends

from vrf.adapters.inbound.api.deps import (
    actualizar_obra_uc,
    agregar_part_uc,
    crear_obra_uc,
    current_user,
    listar_obras_uc,
    obtener_obra_uc,
    quitar_part_uc,
)
from vrf.adapters.inbound.api.schemas import ObraIn, ObraPatch, ParticipacionIn
from vrf.adapters.inbound.api.serialize import dump
from vrf.application.use_cases.obras import (
    ActualizarObra,
    AgregarParticipacion,
    CrearObra,
    ListarObras,
    ObtenerObra,
    QuitarParticipacion,
)
from vrf.domain.entities import Usuario
from vrf.domain.enums import EstadoObra, OrigenMantenimiento, TipoTrabajo

router = APIRouter(prefix="/obras", tags=["obras"])


@router.get("")
def listar(
    cliente_id: UUID | None = None,
    actor: Usuario = Depends(current_user),
    uc: ListarObras = Depends(listar_obras_uc),
) -> list:
    return [dump(x) for x in uc.execute(actor, cliente_id)]


@router.get("/{obra_id}")
def obtener(
    obra_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ObtenerObra = Depends(obtener_obra_uc),
) -> dict:
    return dump(uc.execute(actor, obra_id))


@router.post("")
def crear(
    body: ObraIn,
    actor: Usuario = Depends(current_user),
    uc: CrearObra = Depends(crear_obra_uc),
) -> dict:
    origen = OrigenMantenimiento(body.origen_mantenimiento) if body.origen_mantenimiento else None
    return dump(
        uc.execute(
            actor=actor,
            cliente_id=body.cliente_id,
            nombre=body.nombre,
            direccion=body.direccion,
            tipo_trabajo=TipoTrabajo(body.tipo_trabajo),
            empresa_ids=body.empresa_ids,
            origen_mantenimiento=origen,
            obra_origen_id=body.obra_origen_id,
            origen_terceros_nota=body.origen_terceros_nota,
            sustituye=body.sustituye,
            notas_equipo=body.notas_equipo,
        )
    )


@router.patch("/{obra_id}")
def patch_obra(
    obra_id: UUID,
    body: ObraPatch,
    actor: Usuario = Depends(current_user),
    uc: ActualizarObra = Depends(actualizar_obra_uc),
) -> dict:
    estado = EstadoObra(body.estado) if body.estado else None
    return dump(
        uc.execute(
            actor,
            obra_id,
            body.nombre,
            body.direccion,
            estado,
            body.notas_equipo,
            notas_equipo_set="notas_equipo" in body.model_fields_set,
        )
    )


@router.post("/{obra_id}/participantes")
def agregar(
    obra_id: UUID,
    body: ParticipacionIn,
    actor: Usuario = Depends(current_user),
    uc: AgregarParticipacion = Depends(agregar_part_uc),
) -> dict:
    return dump(uc.execute(actor, obra_id, body.empresa_id))


@router.delete("/{obra_id}/participantes/{empresa_id}")
def quitar(
    obra_id: UUID,
    empresa_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: QuitarParticipacion = Depends(quitar_part_uc),
) -> dict:
    return dump(uc.execute(actor, obra_id, empresa_id))
