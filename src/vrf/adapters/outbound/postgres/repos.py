from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from vrf.adapters.outbound.postgres import mappers as map_
from vrf.adapters.outbound.postgres import models as m
from vrf.domain.entities import (
    Cliente,
    Comprobante,
    Empresa,
    Especialidad,
    Obra,
    Proveedor,
    RefreshToken,
    Rubro,
    TipoPago,
    Usuario,
)


class EspecialidadRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get(self, id: UUID) -> Especialidad | None:
        row = self._s.get(m.EspecialidadModel, id)
        return map_.especialidad(row) if row else None

    def list_by_grupo(self, grupo_id: UUID) -> list[Especialidad]:
        rows = self._s.scalars(select(m.EspecialidadModel).where(m.EspecialidadModel.grupo_id == grupo_id))
        return [map_.especialidad(r) for r in rows]

    def add(self, item: Especialidad) -> None:
        self._s.add(
            m.EspecialidadModel(id=item.id, grupo_id=item.grupo_id, nombre=item.nombre, slug=item.slug)
        )

    def get_by_slug(self, grupo_id: UUID, slug: str) -> Especialidad | None:
        row = self._s.scalars(
            select(m.EspecialidadModel).where(
                m.EspecialidadModel.grupo_id == grupo_id, m.EspecialidadModel.slug == slug
            )
        ).first()
        return map_.especialidad(row) if row else None

    def save(self, item: Especialidad) -> None:
        row = self._s.get(m.EspecialidadModel, item.id)
        if row is None:
            return
        row.nombre = item.nombre
        row.slug = item.slug


class EmpresaRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get(self, id: UUID) -> Empresa | None:
        row = self._s.get(m.EmpresaModel, id)
        return map_.empresa(row) if row else None

    def list_by_grupo(self, grupo_id: UUID) -> list[Empresa]:
        rows = self._s.scalars(select(m.EmpresaModel).where(m.EmpresaModel.grupo_id == grupo_id))
        return [map_.empresa(r) for r in rows]

    def get_by_cuit(self, cuit: str) -> Empresa | None:
        row = self._s.scalars(select(m.EmpresaModel).where(m.EmpresaModel.cuit == cuit)).first()
        return map_.empresa(row) if row else None

    def add(self, item: Empresa) -> None:
        self._s.add(
            m.EmpresaModel(
                id=item.id,
                grupo_id=item.grupo_id,
                razon_social=item.razon_social,
                cuit=item.cuit,
                especialidad_id=item.especialidad_id,
                activa=item.activa,
            )
        )

    def list_by_ids(self, ids: list[UUID]) -> list[Empresa]:
        if not ids:
            return []
        rows = self._s.scalars(select(m.EmpresaModel).where(m.EmpresaModel.id.in_(ids)))
        return [map_.empresa(r) for r in rows]

    def save(self, item: Empresa) -> None:
        row = self._s.get(m.EmpresaModel, item.id)
        if row is None:
            return
        row.razon_social = item.razon_social
        row.cuit = item.cuit
        row.especialidad_id = item.especialidad_id
        row.activa = item.activa


class ClienteRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get(self, id: UUID) -> Cliente | None:
        row = self._s.get(m.ClienteModel, id)
        return map_.cliente(row) if row else None

    def list_by_grupo(self, grupo_id: UUID) -> list[Cliente]:
        rows = self._s.scalars(select(m.ClienteModel).where(m.ClienteModel.grupo_id == grupo_id))
        return [map_.cliente(r) for r in rows]

    def get_by_nombre(self, grupo_id: UUID, nombre: str) -> Cliente | None:
        row = self._s.scalars(
            select(m.ClienteModel).where(
                m.ClienteModel.grupo_id == grupo_id, m.ClienteModel.nombre == nombre
            )
        ).first()
        return map_.cliente(row) if row else None

    def add(self, item: Cliente) -> None:
        self._s.add(
            m.ClienteModel(
                id=item.id, grupo_id=item.grupo_id, nombre=item.nombre, cuit=item.cuit, activo=item.activo
            )
        )

    def save(self, item: Cliente) -> None:
        row = self._s.get(m.ClienteModel, item.id)
        if row is None:
            return
        row.nombre = item.nombre
        row.cuit = item.cuit
        row.activo = item.activo


class ObraRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get(self, id: UUID) -> Obra | None:
        row = self._s.get(m.ObraModel, id)
        return map_.obra(row) if row else None

    def list_by_cliente(self, cliente_id: UUID) -> list[Obra]:
        rows = self._s.scalars(select(m.ObraModel).where(m.ObraModel.cliente_id == cliente_id))
        return [map_.obra(r) for r in rows]

    def list_by_grupo(self, grupo_id: UUID) -> list[Obra]:
        rows = self._s.scalars(
            select(m.ObraModel)
            .join(m.ClienteModel, m.ObraModel.cliente_id == m.ClienteModel.id)
            .where(m.ClienteModel.grupo_id == grupo_id)
        )
        return [map_.obra(r) for r in rows]

    def add(self, item: Obra) -> None:
        row = m.ObraModel(
            id=item.id,
            cliente_id=item.cliente_id,
            nombre=item.nombre,
            direccion=item.direccion,
            tipo_trabajo=item.tipo_trabajo.value,
            origen_mantenimiento=item.origen_mantenimiento.value if item.origen_mantenimiento else None,
            obra_origen_id=item.obra_origen_id,
            origen_terceros_nota=item.origen_terceros_nota,
            sustituye=item.sustituye,
            notas_equipo=item.notas_equipo,
            estado=item.estado.value,
            participantes=[m.ObraEmpresaModel(obra_id=item.id, empresa_id=eid) for eid in item.empresa_ids],
        )
        self._s.add(row)

    def save(self, item: Obra) -> None:
        row = self._s.get(m.ObraModel, item.id)
        if row is None:
            return
        row.nombre = item.nombre
        row.direccion = item.direccion
        row.estado = item.estado.value
        row.notas_equipo = item.notas_equipo
        row.participantes.clear()
        self._s.flush()
        for eid in item.empresa_ids:
            self._s.add(m.ObraEmpresaModel(obra_id=item.id, empresa_id=eid))

    def tiene_comprobantes_vivos(self, obra_id: UUID, empresa_id: UUID) -> bool:
        row = self._s.scalars(
            select(m.ComprobanteModel.id).where(
                m.ComprobanteModel.obra_id == obra_id,
                m.ComprobanteModel.empresa_id == empresa_id,
                m.ComprobanteModel.estado_pago != "anulado",
            )
        ).first()
        return row is not None


class UsuarioRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get(self, id: UUID) -> Usuario | None:
        row = self._s.get(m.UsuarioModel, id)
        return map_.usuario(row) if row else None

    def get_by_email(self, email: str) -> Usuario | None:
        row = self._s.scalars(select(m.UsuarioModel).where(m.UsuarioModel.email == email)).first()
        return map_.usuario(row) if row else None

    def list_by_grupo(self, grupo_id: UUID) -> list[Usuario]:
        rows = self._s.scalars(select(m.UsuarioModel).where(m.UsuarioModel.grupo_id == grupo_id))
        return [map_.usuario(r) for r in rows]

    def add(self, item: Usuario) -> None:
        self._s.add(
            m.UsuarioModel(
                id=item.id,
                grupo_id=item.grupo_id,
                email=item.email,
                password_hash=item.password_hash,
                rol=item.rol.value,
                activo=item.activo,
                empresas=[m.UsuarioEmpresaModel(usuario_id=item.id, empresa_id=e) for e in item.empresa_ids],
            )
        )

    def save(self, item: Usuario) -> None:
        row = self._s.get(m.UsuarioModel, item.id)
        if row is None:
            return
        row.email = item.email
        row.password_hash = item.password_hash
        row.rol = item.rol.value
        row.activo = item.activo
        row.empresas.clear()
        self._s.flush()
        for eid in item.empresa_ids:
            self._s.add(m.UsuarioEmpresaModel(usuario_id=item.id, empresa_id=eid))


class ProveedorRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get(self, id: UUID) -> Proveedor | None:
        row = self._s.get(m.ProveedorModel, id)
        return map_.proveedor(row) if row else None

    def list_by_grupo(self, grupo_id: UUID) -> list[Proveedor]:
        rows = self._s.scalars(select(m.ProveedorModel).where(m.ProveedorModel.grupo_id == grupo_id))
        return [map_.proveedor(r) for r in rows]

    def get_by_cuit(self, cuit: str) -> Proveedor | None:
        row = self._s.scalars(select(m.ProveedorModel).where(m.ProveedorModel.cuit == cuit)).first()
        return map_.proveedor(row) if row else None

    def add(self, item: Proveedor) -> None:
        self._s.add(
            m.ProveedorModel(
                id=item.id,
                grupo_id=item.grupo_id,
                razon_social=item.razon_social,
                cuit=item.cuit,
                notas=item.notas,
            )
        )

    def save(self, item: Proveedor) -> None:
        row = self._s.get(m.ProveedorModel, item.id)
        if row is None:
            return
        row.razon_social = item.razon_social
        row.cuit = item.cuit
        row.notas = item.notas


class RubroRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get(self, id: UUID) -> Rubro | None:
        row = self._s.get(m.RubroModel, id)
        return map_.rubro(row) if row else None

    def list_by_empresa(self, empresa_id: UUID) -> list[Rubro]:
        rows = self._s.scalars(select(m.RubroModel).where(m.RubroModel.empresa_id == empresa_id))
        return [map_.rubro(r) for r in rows]

    def add(self, item: Rubro) -> None:
        self._s.add(
            m.RubroModel(
                id=item.id,
                empresa_id=item.empresa_id,
                nombre=item.nombre,
                clase=item.clase.value,
                ambito=item.ambito.value,
                activo=item.activo,
            )
        )

    def save(self, item: Rubro) -> None:
        row = self._s.get(m.RubroModel, item.id)
        if row is None:
            return
        row.nombre = item.nombre
        row.clase = item.clase.value
        row.ambito = item.ambito.value
        row.activo = item.activo


class TipoPagoRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get(self, id: UUID) -> TipoPago | None:
        row = self._s.get(m.TipoPagoModel, id)
        return map_.tipo_pago(row) if row else None

    def list_by_empresa(self, empresa_id: UUID) -> list[TipoPago]:
        rows = self._s.scalars(select(m.TipoPagoModel).where(m.TipoPagoModel.empresa_id == empresa_id))
        return [map_.tipo_pago(r) for r in rows]

    def add(self, item: TipoPago) -> None:
        self._s.add(
            m.TipoPagoModel(
                id=item.id,
                empresa_id=item.empresa_id,
                nombre=item.nombre,
                schema_extra=item.schema_extra,
                activo=item.activo,
            )
        )

    def save(self, item: TipoPago) -> None:
        row = self._s.get(m.TipoPagoModel, item.id)
        if row is None:
            return
        row.nombre = item.nombre
        row.schema_extra = item.schema_extra
        row.activo = item.activo


class RefreshTokenRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def add(self, item: RefreshToken) -> None:
        self._s.add(
            m.RefreshTokenModel(
                id=item.id,
                usuario_id=item.usuario_id,
                token_hash=item.token_hash,
                expira=item.expira,
                revocado=item.revocado,
            )
        )

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        row = self._s.scalars(
            select(m.RefreshTokenModel).where(m.RefreshTokenModel.token_hash == token_hash)
        ).first()
        return map_.refresh(row) if row else None

    def revoke(self, token_hash: str) -> None:
        row = self._s.scalars(
            select(m.RefreshTokenModel).where(m.RefreshTokenModel.token_hash == token_hash)
        ).first()
        if row:
            row.revocado = True


class GrupoRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get_unico(self) -> tuple:
        row = self._s.scalars(select(m.GrupoModel)).first()
        if row is None:
            raise RuntimeError("Falta semilla de grupo")
        return row.id, row.nombre

    def ensure_seed_grupo(self, nombre: str, dueno: str):
        row = self._s.scalars(select(m.GrupoModel)).first()
        if row:
            return row.id
        from uuid import uuid4

        gid = uuid4()
        self._s.add(m.GrupoModel(id=gid, nombre=nombre, dueno=dueno, activo=True))
        return gid


class ComprobanteRepo:
    def __init__(self, s: Session) -> None:
        self._s = s

    def get(self, id: UUID) -> Comprobante | None:
        row = self._s.get(m.ComprobanteModel, id)
        return map_.comprobante(row) if row else None

    def add(self, item: Comprobante) -> None:
        row = self._row_from_entity(item)
        self._s.add(row)

    def save(self, item: Comprobante) -> None:
        row = self._s.get(m.ComprobanteModel, item.id)
        if row is None:
            return
        self._apply(row, item)
        if item.archivo:
            if row.archivo is None:
                row.archivo = m.ArchivoModel(
                    id=item.archivo.id,
                    comprobante_id=item.id,
                    nombre_original=item.archivo.nombre_original,
                    mime=item.archivo.mime,
                    path=item.archivo.path,
                    sha256=item.archivo.sha256,
                    size=item.archivo.size,
                )
            else:
                row.archivo.nombre_original = item.archivo.nombre_original
                row.archivo.mime = item.archivo.mime
                row.archivo.path = item.archivo.path
                row.archivo.sha256 = item.archivo.sha256
                row.archivo.size = item.archivo.size

    def get_by_clave_afip(
        self, cuit_emisor: str, tipo_afip: str, punto_venta: int, numero: int
    ) -> Comprobante | None:
        row = self._s.scalars(
            select(m.ComprobanteModel).where(
                m.ComprobanteModel.cuit_emisor == cuit_emisor,
                m.ComprobanteModel.tipo_afip == tipo_afip,
                m.ComprobanteModel.punto_venta == punto_venta,
                m.ComprobanteModel.numero == numero,
            )
        ).first()
        return map_.comprobante(row) if row else None

    def listar(
        self,
        empresa_id: UUID | None = None,
        obra_id: UUID | None = None,
        estado_pago: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        cliente_id: UUID | None = None,
        proveedor_id: UUID | None = None,
        clasificacion: str | None = None,
        rubro_id: UUID | None = None,
        tipo_pago_id: UUID | None = None,
        q: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Comprobante]:
        stmt = select(m.ComprobanteModel)
        if cliente_id:
            stmt = stmt.join(m.ObraModel, m.ComprobanteModel.obra_id == m.ObraModel.id).where(
                m.ObraModel.cliente_id == cliente_id
            )
        if empresa_id:
            stmt = stmt.where(m.ComprobanteModel.empresa_id == empresa_id)
        if obra_id:
            stmt = stmt.where(m.ComprobanteModel.obra_id == obra_id)
        if estado_pago:
            stmt = stmt.where(m.ComprobanteModel.estado_pago == estado_pago)
        if desde:
            stmt = stmt.where(m.ComprobanteModel.fecha >= desde)
        if hasta:
            stmt = stmt.where(m.ComprobanteModel.fecha <= hasta)
        if proveedor_id:
            stmt = stmt.where(m.ComprobanteModel.proveedor_id == proveedor_id)
        if clasificacion:
            stmt = stmt.where(m.ComprobanteModel.clasificacion == clasificacion)
        if rubro_id:
            stmt = stmt.where(m.ComprobanteModel.rubro_id == rubro_id)
        if tipo_pago_id:
            stmt = stmt.where(m.ComprobanteModel.tipo_pago_id == tipo_pago_id)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                m.ComprobanteModel.numero_comprobante.ilike(like)
                | m.ComprobanteModel.nota.ilike(like)
                | m.ComprobanteModel.cuit_emisor.ilike(like)
            )
        stmt = stmt.order_by(m.ComprobanteModel.fecha.desc()).offset(offset).limit(limit)
        return [map_.comprobante(r) for r in self._s.scalars(stmt)]

    def posible_duplicado_foto(
        self, sha256: str, proveedor_id: UUID | None, numero: int | None, fecha
    ) -> Comprobante | None:
        por_hash = self._s.scalars(
            select(m.ComprobanteModel)
            .join(m.ArchivoModel, m.ArchivoModel.comprobante_id == m.ComprobanteModel.id)
            .where(m.ArchivoModel.sha256 == sha256)
        ).first()
        if por_hash:
            return map_.comprobante(por_hash)
        if proveedor_id and numero is not None:
            row = self._s.scalars(
                select(m.ComprobanteModel).where(
                    m.ComprobanteModel.proveedor_id == proveedor_id,
                    m.ComprobanteModel.numero == numero,
                    m.ComprobanteModel.fecha == fecha,
                    m.ComprobanteModel.tipo_afip.notin_(("A", "B", "C")),
                )
            ).first()
            return map_.comprobante(row) if row else None
        return None

    def tiene_vivos(self, obra_id: UUID, empresa_id: UUID) -> bool:
        row = self._s.scalars(
            select(m.ComprobanteModel.id).where(
                m.ComprobanteModel.obra_id == obra_id,
                m.ComprobanteModel.empresa_id == empresa_id,
                m.ComprobanteModel.estado_pago != "anulado",
            )
        ).first()
        return row is not None

    def _row_from_entity(self, item: Comprobante) -> m.ComprobanteModel:
        row = m.ComprobanteModel(id=item.id)
        self._apply(row, item)
        if item.archivo:
            row.archivo = m.ArchivoModel(
                id=item.archivo.id,
                comprobante_id=item.id,
                nombre_original=item.archivo.nombre_original,
                mime=item.archivo.mime,
                path=item.archivo.path,
                sha256=item.archivo.sha256,
                size=item.archivo.size,
            )
        return row

    def _apply(self, row: m.ComprobanteModel, item: Comprobante) -> None:
        row.empresa_id = item.empresa_id
        row.obra_id = item.obra_id
        row.proveedor_id = item.proveedor_id
        row.usuario_id = item.usuario_id
        row.clasificacion = item.clasificacion.value
        row.rubro_id = item.rubro_id
        row.tipo_pago_id = item.tipo_pago_id
        row.tipo_afip = item.tipo_afip.value
        row.punto_venta = item.punto_venta
        row.numero = item.numero
        row.numero_comprobante = item.numero_comprobante
        row.fecha = item.fecha
        row.neto_21 = item.neto_21
        row.iva_21 = item.iva_21
        row.neto_105 = item.neto_105
        row.iva_105 = item.iva_105
        row.neto_27 = item.neto_27
        row.iva_27 = item.iva_27
        row.no_gravado = item.no_gravado
        row.percep_iva = item.percep_iva
        row.percep_iibb = item.percep_iibb
        row.total = item.total
        row.estado_pago = item.estado_pago.value
        row.cuit_emisor = item.cuit_emisor
        row.nota = item.nota
        row.extra = item.extra or {}
        row.comprobado_en = item.comprobado_en
        row.comprobado_por = item.comprobado_por
        row.anulado_at = item.anulado_at
        row.created_at = item.created_at
