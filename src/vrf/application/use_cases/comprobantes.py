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
    nombre_original: str | None = None
    mime: str | None = None
    contenido: bytes | None = None
    numero_comprobante: str | None = None


def formatear_numero_comprobante(
    numero_comprobante: str | None, punto_venta: int | None, numero: int | None
) -> str | None:
    if numero_comprobante and numero_comprobante.strip():
        return numero_comprobante.strip()
    if punto_venta is not None and numero is not None:
        return f"{punto_venta:04d}-{numero:08d}"
    if numero is not None:
        return str(numero)
    return None


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

    def execute(self, actor: Usuario, datos: DatosAlta, *, commit: bool = True) -> dict:
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
        archivo = None
        aviso = None
        sha = None
        if datos.contenido:
            stored = self._storage.save(
                datos.contenido,
                datos.nombre_original or "archivo",
                datos.mime or "application/octet-stream",
            )
            sha = stored.sha256
            archivo = Archivo(
                id=uuid4(),
                comprobante_id=cid,
                nombre_original=stored.nombre_original,
                mime=stored.mime,
                path=stored.path,
                sha256=stored.sha256,
                size=stored.size,
            )
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
            numero_comprobante=formatear_numero_comprobante(
                datos.numero_comprobante, datos.punto_venta, datos.numero
            ),
            nota=datos.nota,
            extra=datos.extra or {},
            comprobado_en=ahora if datos.ya_pagada else None,
            comprobado_por=actor.id if datos.ya_pagada else None,
            created_at=ahora,
            archivo=archivo,
        )
        if clave is None and sha:
            otro = self._comps.posible_duplicado_foto(
                sha, datos.proveedor_id, datos.numero, datos.fecha
            )
            if otro:
                aviso = str(otro.id)
        self._comps.add(item)
        if commit:
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
    ) -> list[Comprobante]:
        if empresa_id:
            exigir_empresa_actor(actor, empresa_id)
        lim = max(1, min(limit, 2000))
        off = max(0, offset)
        filas = self._comps.listar(
            empresa_id=empresa_id,
            obra_id=obra_id,
            estado_pago=estado_pago,
            desde=desde,
            hasta=hasta,
            cliente_id=cliente_id,
            proveedor_id=proveedor_id,
            clasificacion=clasificacion,
            rubro_id=rubro_id,
            tipo_pago_id=tipo_pago_id,
            q=q,
            limit=lim,
            offset=off,
        )
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
    """Corrige solo organización: obra, clasificación, rubro / tipo de pago.

    Fecha, número, importes, proveedor y cliente no se editan aquí
    (el cliente viene de la obra).
    """

    def __init__(
        self,
        comps: ComprobanteRepository,
        obras: ObraRepository,
        rubros: RubroRepository,
        tipos: TipoPagoRepository,
        uow: UnitOfWork,
    ) -> None:
        self._comps = comps
        self._obras = obras
        self._rubros = rubros
        self._tipos = tipos
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        comprobante_id: UUID,
        *,
        obra_id: UUID | None = None,
        rubro_id: UUID | None = None,
        tipo_pago_id: UUID | None = None,
        clasificacion: Clasificacion | None = None,
        clear_obra: bool = False,
    ) -> Comprobante:
        item = self._comps.get(comprobante_id)
        if item is None:
            raise NotFound("Comprobante inexistente")
        exigir_empresa_actor(actor, item.empresa_id)
        validar_editable(item.estado_pago)
        if clasificacion is not None:
            item.clasificacion = clasificacion
            if clasificacion == Clasificacion.PAGO:
                item.rubro_id = None
            else:
                item.tipo_pago_id = None
        if clear_obra:
            item.obra_id = None
        elif obra_id is not None:
            obra = self._obras.get(obra_id)
            if obra is None:
                raise NotFound("Obra inexistente")
            validar_imputacion(obra, item.empresa_id)
            item.obra_id = obra_id
        if rubro_id is not None:
            rubro = self._rubros.get(rubro_id)
            if rubro is None or rubro.empresa_id != item.empresa_id:
                raise NotFound("Rubro inexistente en esa empresa")
            item.rubro_id = rubro_id
            item.tipo_pago_id = None
        if tipo_pago_id is not None:
            tipo = self._tipos.get(tipo_pago_id)
            if tipo is None or tipo.empresa_id != item.empresa_id:
                raise NotFound("Tipo de pago inexistente en esa empresa")
            item.tipo_pago_id = tipo_pago_id
            item.rubro_id = None
        validar_clasificacion(item.clasificacion, item.rubro_id, item.tipo_pago_id)
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
