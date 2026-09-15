from uuid import UUID

from vrf.domain.entities import Empresa, Obra
from vrf.domain.enums import OrigenMantenimiento, TipoTrabajo
from vrf.domain.exceptions import InvalidInput


def validar_alta_obra(
    tipo: TipoTrabajo,
    origen: OrigenMantenimiento | None,
    obra_origen: Obra | None,
    cliente_id: UUID,
    origen_terceros_nota: str | None,
    sustituye: str | None,
    empresa_ids: list[UUID],
    empresas: list[Empresa],
    cliente_grupo_id: UUID,
) -> None:
    if not empresa_ids:
        raise InvalidInput("La obra necesita al menos una empresa")
    if len(set(empresa_ids)) != len(empresa_ids):
        raise InvalidInput("Empresas duplicadas")
    por_id = {e.id: e for e in empresas}
    if any(eid not in por_id for eid in empresa_ids):
        raise InvalidInput("Empresa inexistente")
    if any(por_id[eid].grupo_id != cliente_grupo_id for eid in empresa_ids):
        raise InvalidInput("La empresa no es del mismo grupo que el cliente")

    if tipo == TipoTrabajo.INSTALACION:
        if origen is not None or obra_origen is not None:
            raise InvalidInput("Una instalación no lleva origen de mantenimiento")
        return

    if origen is None:
        raise InvalidInput("El mantenimiento exige origen")

    if origen == OrigenMantenimiento.INSTALACION_REGISTRADA:
        if obra_origen is None:
            raise InvalidInput("Falta la obra de instalación registrada")
        if obra_origen.tipo_trabajo != TipoTrabajo.INSTALACION:
            raise InvalidInput("La obra origen debe ser instalación")
        if obra_origen.cliente_id != cliente_id:
            raise InvalidInput("La obra origen debe ser del mismo cliente")
        return

    if origen == OrigenMantenimiento.TERCEROS:
        if obra_origen is not None:
            raise InvalidInput("Terceros no lleva obra origen")
        if not (origen_terceros_nota or "").strip():
            raise InvalidInput("Terceros exige nota de quién instaló")
        return

    if origen == OrigenMantenimiento.MANTENIMIENTO_SUSTITUCION:
        if not (sustituye or "").strip():
            raise InvalidInput("Sustitución exige qué se reemplaza")
        if obra_origen is not None:
            if obra_origen.tipo_trabajo != TipoTrabajo.INSTALACION:
                raise InvalidInput("La obra origen debe ser instalación")
            if obra_origen.cliente_id != cliente_id:
                raise InvalidInput("La obra origen debe ser del mismo cliente")


def validar_quitar_participacion(obra: Obra, empresa_id: UUID, tiene_comprobantes: bool) -> None:
    if empresa_id not in obra.empresa_ids:
        raise InvalidInput("Esa empresa no participa")
    if tiene_comprobantes:
        raise InvalidInput("No se quita una empresa con comprobantes no anulados")
    if len(obra.empresa_ids) <= 1:
        raise InvalidInput("La obra debe quedar con al menos una empresa")
