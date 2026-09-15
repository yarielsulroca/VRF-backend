from uuid import UUID, uuid4

from vrf.domain.entities import Obra, Usuario
from vrf.domain.enums import EstadoObra, OrigenMantenimiento, Rol, TipoTrabajo
from vrf.domain.exceptions import Forbidden, NotFound
from vrf.domain.obra_reglas import validar_alta_obra, validar_quitar_participacion
from vrf.domain.ports.repositories import (
    ClienteRepository,
    EmpresaRepository,
    ObraRepository,
    UnitOfWork,
)


class CrearObra:
    def __init__(
        self,
        obras: ObraRepository,
        clientes: ClienteRepository,
        empresas: EmpresaRepository,
        uow: UnitOfWork,
    ) -> None:
        self._obras = obras
        self._clientes = clientes
        self._empresas = empresas
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        cliente_id: UUID,
        nombre: str,
        direccion: str,
        tipo_trabajo: TipoTrabajo,
        empresa_ids: list[UUID],
        origen_mantenimiento: OrigenMantenimiento | None,
        obra_origen_id: UUID | None,
        origen_terceros_nota: str | None,
        sustituye: str | None,
        notas_equipo: str | None,
    ) -> Obra:
        if actor.rol != Rol.ADMIN:
            if any(eid not in actor.empresa_ids for eid in empresa_ids):
                raise Forbidden("Solo podés asociar empresas habilitadas")
        cliente = self._clientes.get(cliente_id)
        if cliente is None:
            raise NotFound("Cliente inexistente")
        empresas = self._empresas.list_by_ids(empresa_ids)
        origen = self._obras.get(obra_origen_id) if obra_origen_id else None
        validar_alta_obra(
            tipo=tipo_trabajo,
            origen=origen_mantenimiento,
            obra_origen=origen,
            cliente_id=cliente_id,
            origen_terceros_nota=origen_terceros_nota,
            sustituye=sustituye,
            empresa_ids=empresa_ids,
            empresas=empresas,
            cliente_grupo_id=cliente.grupo_id,
        )
        obra = Obra(
            id=uuid4(),
            cliente_id=cliente_id,
            nombre=nombre,
            direccion=direccion,
            tipo_trabajo=tipo_trabajo,
            estado=EstadoObra.ABIERTA,
            empresa_ids=list(empresa_ids),
            origen_mantenimiento=origen_mantenimiento,
            obra_origen_id=obra_origen_id,
            origen_terceros_nota=origen_terceros_nota,
            sustituye=sustituye,
            notas_equipo=notas_equipo,
        )
        self._obras.add(obra)
        self._uow.commit()
        return obra


class ListarObras:
    def __init__(self, obras: ObraRepository, clientes: ClienteRepository) -> None:
        self._obras = obras
        self._clientes = clientes

    def execute(self, actor: Usuario, cliente_id: UUID | None) -> list[Obra]:
        if cliente_id:
            filas = self._obras.list_by_cliente(cliente_id)
        else:
            filas = self._obras.list_by_grupo(actor.grupo_id)
        if actor.rol == Rol.ADMIN:
            return filas
        permitidas = set(actor.empresa_ids)
        return [o for o in filas if permitidas.intersection(o.empresa_ids)]


class ObtenerObra:
    def __init__(self, obras: ObraRepository) -> None:
        self._obras = obras

    def execute(self, actor: Usuario, obra_id: UUID) -> Obra:
        obra = self._obras.get(obra_id)
        if obra is None:
            raise NotFound("Obra inexistente")
        if actor.rol != Rol.ADMIN and not set(actor.empresa_ids).intersection(obra.empresa_ids):
            raise Forbidden()
        return obra


class QuitarParticipacion:
    def __init__(self, obras: ObraRepository, uow: UnitOfWork) -> None:
        self._obras = obras
        self._uow = uow

    def execute(self, actor: Usuario, obra_id: UUID, empresa_id: UUID) -> Obra:
        if actor.rol != Rol.ADMIN:
            raise Forbidden("Solo el admin quita participantes")
        obra = self._obras.get(obra_id)
        if obra is None:
            raise NotFound("Obra inexistente")
        vivos = self._obras.tiene_comprobantes_vivos(obra_id, empresa_id)
        validar_quitar_participacion(obra, empresa_id, vivos)
        obra.empresa_ids = [e for e in obra.empresa_ids if e != empresa_id]
        self._obras.save(obra)
        self._uow.commit()
        return obra


class AgregarParticipacion:
    def __init__(
        self,
        obras: ObraRepository,
        empresas: EmpresaRepository,
        clientes: ClienteRepository,
        uow: UnitOfWork,
    ) -> None:
        self._obras = obras
        self._empresas = empresas
        self._clientes = clientes
        self._uow = uow

    def execute(self, actor: Usuario, obra_id: UUID, empresa_id: UUID) -> Obra:
        if actor.rol != Rol.ADMIN:
            raise Forbidden("Solo el admin agrega participantes")
        obra = self._obras.get(obra_id)
        if obra is None:
            raise NotFound("Obra inexistente")
        empresa = self._empresas.get(empresa_id)
        cliente = self._clientes.get(obra.cliente_id)
        if empresa is None or cliente is None:
            raise NotFound("Empresa o cliente inexistente")
        if empresa.grupo_id != cliente.grupo_id:
            raise Forbidden("La empresa no es del grupo")
        if empresa_id not in obra.empresa_ids:
            obra.empresa_ids.append(empresa_id)
            self._obras.save(obra)
            self._uow.commit()
        return obra


class ActualizarObra:
    def __init__(self, obras: ObraRepository, uow: UnitOfWork) -> None:
        self._obras = obras
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        obra_id: UUID,
        nombre: str | None = None,
        direccion: str | None = None,
        estado: EstadoObra | None = None,
        notas_equipo: str | None = None,
        notas_equipo_set: bool = False,
    ) -> Obra:
        if actor.rol != Rol.ADMIN:
            raise Forbidden("Solo el admin edita la obra")
        obra = self._obras.get(obra_id)
        if obra is None:
            raise NotFound("Obra inexistente")
        if nombre is not None:
            obra.nombre = nombre
        if direccion is not None:
            obra.direccion = direccion
        if estado is not None:
            obra.estado = estado
        if notas_equipo_set:
            obra.notas_equipo = notas_equipo
        self._obras.save(obra)
        self._uow.commit()
        return obra
