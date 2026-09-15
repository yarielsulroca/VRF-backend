from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends

from vrf.adapters.inbound.api.deps import costos_obra_uc, current_user, dashboard_uc, listar_costos_uc
from vrf.adapters.inbound.api.serialize import dump
from vrf.application.use_cases.consultas import ConsultarCostosObra, ConsultarDashboard, ListarCostos
from vrf.domain.entities import Usuario

router = APIRouter(tags=["consultas"])


@router.get("/dashboard")
def dashboard(
    mes: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    empresa_id: UUID | None = None,
    actor: Usuario = Depends(current_user),
    uc: ConsultarDashboard = Depends(dashboard_uc),
) -> dict:
    return dump(uc.execute(actor, mes=mes, desde=desde, hasta=hasta, empresa_id=empresa_id))


@router.get("/costos")
def listar_costos(
    cliente_id: UUID | None = None,
    actor: Usuario = Depends(current_user),
    uc: ListarCostos = Depends(listar_costos_uc),
) -> dict:
    return dump(uc.execute(actor, cliente_id))


@router.get("/costos/obras/{obra_id}")
def costos_obra(
    obra_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ConsultarCostosObra = Depends(costos_obra_uc),
) -> dict:
    return dump(uc.execute(actor, obra_id))
