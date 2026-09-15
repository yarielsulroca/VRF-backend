import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from vrf.domain.comprobante_reglas import (
    exigir_empresa_actor,
    validar_afip_completo,
    validar_clasificacion,
    validar_editable,
    validar_imputacion,
    validar_iva,
    validar_transicion,
)
from vrf.domain.entities import Archivo, Comprobante, Usuario
from vrf.domain.enums import Clasificacion, EstadoPago, Rol, TipoAfip
from vrf.domain.exceptions import Conflict, NotFound
from vrf.domain.ports.repositories import (
    ComprobanteRepository,
    EmpresaRepository,
    ObraRepository,
    ProveedorRepository,
    RubroRepository,
    TipoPagoRepository,
    UnitOfWork,
    UsuarioRepository,
)
from vrf.domain.ports.security import Clock
from vrf.domain.ports.storage import ArchivoStorage
from vrf.domain.vos import dinero

log = logging.getLogger("vrf.comprobantes")


@dataclass
class DatosAlta:
    empresa_id: UUID
    obra_id: UUID | None
    proveedor_id: UUID | None
    clasificacion: Clasificacion
    rubro_id: UUID | None
    tipo_pago_id: UUID | None
    tipo_afip: TipoAfip
    punto_venta: int | None
    numero: int | None
    fecha: date
    neto_21: Decimal
    iva_21: Decimal
    neto_105: Decimal
    iva_105: Decimal
    neto_27: Decimal
    iva_27: Decimal
    no_gravado: Decimal
    percep_iva: Decimal
    percep_iibb: Decimal
    total: Decimal
    ya_pagada: bool
    nota: str | None
    extra: dict
    nombre_original: str
    mime: str
    contenido: bytes


def _conflicto_afip(existente: Comprobante, usuarios: UsuarioRepository) -> Conflict:
    user = usuarios.get(existente.usuario_id)
    return Conflict(
        "Comprobante AFIP duplicado",
        extra={
            "obraId": str(existente.obra_id) if existente.obra_id else None,
            "empresaId": str(existente.empresa_id),
            "fechaCarga": existente.created_at.isoformat() if existente.created_at else None,
            "usuario": user.email if user else None,
            "comprobanteId": str(existente.id),
        },
    )


class CrearComprobante:
    def __init__(
        self,
        comps: ComprobanteRepository,
        empresas: EmpresaRepository,
        obras: ObraRepository,
        proveedores: ProveedorRepository,
        rubros: RubroRepository,
        tipos: TipoPagoRepository,
        usuarios: UsuarioRepository,
        storage: ArchivoStorage,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._comps = comps
        self._empresas = empresas
        self._obras = obras
        self._proveedores = proveedores
        self._rubros = rubros
        self._tipos = tipos
        self._usuarios = usuarios
        self._storage = storage
        self._clock = clock
        self._uow = uow

    def execute(self, actor: Usuario, datos: DatosAlta) -> dict:
        exigir_empresa_actor(actor, datos.empresa_id)
        if self._empresas.get(datos.empresa_id) is None:
            raise NotFound("Empresa inexistente")
        obra = self._obras.get(datos.obra_id) if datos.obra_id else None
        if datos.obra_id and obra is None:
            raise NotFound("Obra inexistente")
        validar_imputacion(obra, datos.empresa_id)
        validar_clasificacion(datos.clasificacion, datos.rubro_id, datos.tipo_pago_id)
        if datos.rubro_id:
            rubro = self._rubros.get(datos.rubro_id)
            if rubro is None or rubro.empresa_id != datos.empresa_id:
                raise NotFound("Rubro inexistente en esa empresa")
        if datos.tipo_pago_id:
            tipo = self._tipos.get(datos.tipo_pago_id)
            if tipo is None or tipo.empresa_id != datos.empresa_id:
                raise NotFound("Tipo de pago inexistente en esa empresa")
        cuit_emisor = None
        if datos.proveedor_id:
            proveedor = self._proveedores.get(datos.proveedor_id)
            if proveedor is None:
                raise NotFound("Proveedor inexistente")
            cuit_emisor = proveedor.cuit
        validar_iva(
            datos.neto_21,
            datos.iva_21,
            datos.neto_105,
            datos.iva_105,
            datos.neto_27,
            datos.iva_27,
            datos.no_gravado,
            datos.percep_iva,
            datos.percep_iibb,
            datos.total,
        )
        clave = validar_afip_completo(datos.tipo_afip, cuit_emisor, datos.punto_venta, datos.numero)
        if clave:
            dup = self._comps.get_by_clave_afip(
                clave.cuit_emisor, clave.tipo_afip.value, clave.punto_venta, clave.numero
            )
            if dup:
                log.warning(
                    "duplicado_afip existente=%s cuit=%s tipo=%s pto=%s nro=%s",
                    dup.id,
                    clave.cuit_emisor,
                    clave.tipo_afip.value,
                    clave.punto_venta,
                    clave.numero,
                )
                raise _conflicto_afip(dup, self._usuarios)
        ahora = self._clock.now()
        estado = EstadoPago.COMPROBADO_PAGADO if datos.ya_pagada else EstadoPago.PENDIENTE
        cid = uuid4()
        stored = self._storage.save(datos.contenido, datos.nombre_original, datos.mime)
        item = Comprobante(
            id=cid,
            empresa_id=datos.empresa_id,
            obra_id=datos.obra_id,
            proveedor_id=datos.proveedor_id,
            usuario_id=actor.id,
            clasificacion=datos.clasificacion,
            rubro_id=datos.rubro_id,
            tipo_pago_id=datos.tipo_pago_id,
            tipo_afip=datos.tipo_afip,
            punto_venta=datos.punto_venta,
            numero=datos.numero,
            fecha=datos.fecha,
            neto_21=dinero(datos.neto_21),
            iva_21=dinero(datos.iva_21),
            neto_105=dinero(datos.neto_105),
            iva_105=dinero(datos.iva_105),
            neto_27=dinero(datos.neto_27),
            iva_27=dinero(datos.iva_27),
            no_gravado=dinero(datos.no_gravado),
            percep_iva=dinero(datos.percep_iva),
            percep_iibb=dinero(datos.percep_iibb),
            total=dinero(datos.total),
            estado_pago=estado,
            cuit_emisor=cuit_emisor,
            nota=datos.nota,
            extra=datos.extra or {},
            comprobado_en=ahora if datos.ya_pagada else None,
            comprobado_por=actor.id if datos.ya_pagada else None,
            created_at=ahora,
            archivo=Archivo(
                id=uuid4(),
                comprobante_id=cid,
                nombre_original=stored.nombre_original,
                mime=stored.mime,
                path=stored.path,
                sha256=stored.sha256,
                size=stored.size,
            ),
        )
        aviso = None
        if clave is None:
            otro = self._comps.posible_duplicado_foto(
                stored.sha256, datos.proveedor_id, datos.numero, datos.fecha
            )
            if otro:
                aviso = str(otro.id)
        self._comps.add(item)
        self._uow.commit()
        log.info(
            "carga comprobante_id=%s empresa_id=%s estado=%s duplicado_foto=%s",
            item.id,
            item.empresa_id,
            item.estado_pago.value,
            aviso,
        )
        return {"comprobante": item, "posible_duplicado_id": aviso}


class ListarComprobantes:
    def __init__(self, comps: ComprobanteRepository) -> None:
        self._comps = comps

    def execute(
        self,
        actor: Usuario,
        empresa_id: UUID | None,
        obra_id: UUID | None,
        estado_pago: str | None,
    ) -> list[Comprobante]:
        if empresa_id:
            exigir_empresa_actor(actor, empresa_id)
        filas = self._comps.listar(empresa_id, obra_id, estado_pago)
        if actor.rol == Rol.ADMIN:
            return filas
        permitidas = set(actor.empresa_ids)
        return [c for c in filas if c.empresa_id in permitidas]


class ObtenerComprobante:
    def __init__(self, comps: ComprobanteRepository) -> None:
        self._comps = comps

    def execute(self, actor: Usuario, comprobante_id: UUID) -> Comprobante:
        item = self._comps.get(comprobante_id)
        if item is None:
            raise NotFound("Comprobante inexistente")
        exigir_empresa_actor(actor, item.empresa_id)
        return item


class ActualizarComprobante:
    def __init__(self, comps: ComprobanteRepository, uow: UnitOfWork) -> None:
        self._comps = comps
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        comprobante_id: UUID,
        nota: str | None,
        extra: dict | None,
        total: Decimal | None,
        neto_21: Decimal | None,
        iva_21: Decimal | None,
        neto_105: Decimal | None,
        iva_105: Decimal | None,
        neto_27: Decimal | None,
        iva_27: Decimal | None,
        no_gravado: Decimal | None,
        percep_iva: Decimal | None,
        percep_iibb: Decimal | None,
    ) -> Comprobante:
        item = self._comps.get(comprobante_id)
        if item is None:
            raise NotFound("Comprobante inexistente")
        exigir_empresa_actor(actor, item.empresa_id)
        validar_editable(item.estado_pago)
        if nota is not None:
            item.nota = nota
        if extra is not None:
            item.extra = extra
        if total is not None:
            item.total = dinero(total)
        if neto_21 is not None:
            item.neto_21 = dinero(neto_21)
        if iva_21 is not None:
            item.iva_21 = dinero(iva_21)
        if neto_105 is not None:
            item.neto_105 = dinero(neto_105)
        if iva_105 is not None:
            item.iva_105 = dinero(iva_105)
        if neto_27 is not None:
            item.neto_27 = dinero(neto_27)
        if iva_27 is not None:
            item.iva_27 = dinero(iva_27)
        if no_gravado is not None:
            item.no_gravado = dinero(no_gravado)
        if percep_iva is not None:
            item.percep_iva = dinero(percep_iva)
        if percep_iibb is not None:
            item.percep_iibb = dinero(percep_iibb)
        validar_iva(
            item.neto_21,
            item.iva_21,
            item.neto_105,
            item.iva_105,
            item.neto_27,
            item.iva_27,
            item.no_gravado,
            item.percep_iva,
            item.percep_iibb,
            item.total,
        )
        self._comps.save(item)
        self._uow.commit()
        return item


class ReemplazarArchivo:
    def __init__(
        self, comps: ComprobanteRepository, storage: ArchivoStorage, uow: UnitOfWork
    ) -> None:
        self._comps = comps
        self._storage = storage
        self._uow = uow

    def execute(
        self, actor: Usuario, comprobante_id: UUID, contenido: bytes, nombre: str, mime: str
    ) -> Comprobante:
        item = self._comps.get(comprobante_id)
        if item is None:
            raise NotFound("Comprobante inexistente")
        exigir_empresa_actor(actor, item.empresa_id)
        validar_editable(item.estado_pago)
        stored = self._storage.save(contenido, nombre, mime)
        aid = item.archivo.id if item.archivo else uuid4()
        item.archivo = Archivo(
            id=aid,
            comprobante_id=item.id,
            nombre_original=stored.nombre_original,
            mime=stored.mime,
            path=stored.path,
            sha256=stored.sha256,
            size=stored.size,
        )
        self._comps.save(item)
        self._uow.commit()
        return item


class CambiarEstado:
    def __init__(self, comps: ComprobanteRepository, clock: Clock, uow: UnitOfWork) -> None:
        self._comps = comps
        self._clock = clock
        self._uow = uow

    def execute(self, actor: Usuario, comprobante_id: UUID, hacia: EstadoPago) -> Comprobante:
        item = self._comps.get(comprobante_id)
        if item is None:
            raise NotFound("Comprobante inexistente")
        exigir_empresa_actor(actor, item.empresa_id)
        validar_transicion(item.estado_pago, hacia, actor)
        desde = item.estado_pago
        ahora = self._clock.now()
        if hacia == EstadoPago.COMPROBADO_PAGADO:
            item.comprobado_en = ahora
            item.comprobado_por = actor.id
        if hacia == EstadoPago.PENDIENTE:
            item.comprobado_en = None
            item.comprobado_por = None
        if hacia == EstadoPago.ANULADO:
            item.anulado_at = ahora
        item.estado_pago = hacia
        self._comps.save(item)
        self._uow.commit()
        log.info(
            "estado comprobante_id=%s de=%s a=%s actor=%s",
            item.id,
            desde.value,
            hacia.value,
            actor.id,
        )
        return item


class ServirOriginal:
    def __init__(self, comps: ComprobanteRepository, storage: ArchivoStorage) -> None:
        self._comps = comps
        self._storage = storage

    def execute(self, actor: Usuario, comprobante_id: UUID) -> tuple[Archivo, bytes]:
        item = self._comps.get(comprobante_id)
        if item is None or item.archivo is None:
            raise NotFound("Archivo inexistente")
        exigir_empresa_actor(actor, item.empresa_id)
        return item.archivo, self._storage.read(item.archivo.path)
