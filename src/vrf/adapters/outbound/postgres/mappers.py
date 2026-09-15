from vrf.adapters.outbound.postgres import models as m
from vrf.domain.entities import (
    Archivo,
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
from vrf.domain.enums import (
    AmbitoRubro,
    ClaseRubro,
    Clasificacion,
    EstadoObra,
    EstadoPago,
    OrigenMantenimiento,
    Rol,
    TipoAfip,
    TipoTrabajo,
)


def especialidad(row: m.EspecialidadModel) -> Especialidad:
    return Especialidad(id=row.id, grupo_id=row.grupo_id, nombre=row.nombre, slug=row.slug)


def empresa(row: m.EmpresaModel) -> Empresa:
    return Empresa(
        id=row.id,
        grupo_id=row.grupo_id,
        razon_social=row.razon_social,
        cuit=row.cuit,
        especialidad_id=row.especialidad_id,
        activa=row.activa,
    )


def cliente(row: m.ClienteModel) -> Cliente:
    return Cliente(
        id=row.id, grupo_id=row.grupo_id, nombre=row.nombre, cuit=row.cuit, activo=row.activo
    )


def obra(row: m.ObraModel) -> Obra:
    origen = OrigenMantenimiento(row.origen_mantenimiento) if row.origen_mantenimiento else None
    return Obra(
        id=row.id,
        cliente_id=row.cliente_id,
        nombre=row.nombre,
        direccion=row.direccion,
        tipo_trabajo=TipoTrabajo(row.tipo_trabajo),
        estado=EstadoObra(row.estado),
        empresa_ids=[p.empresa_id for p in row.participantes],
        origen_mantenimiento=origen,
        obra_origen_id=row.obra_origen_id,
        origen_terceros_nota=row.origen_terceros_nota,
        sustituye=row.sustituye,
        notas_equipo=row.notas_equipo,
    )


def usuario(row: m.UsuarioModel) -> Usuario:
    return Usuario(
        id=row.id,
        grupo_id=row.grupo_id,
        email=row.email,
        password_hash=row.password_hash,
        rol=Rol(row.rol),
        activo=row.activo,
        empresa_ids=[e.empresa_id for e in row.empresas],
    )


def proveedor(row: m.ProveedorModel) -> Proveedor:
    return Proveedor(
        id=row.id,
        grupo_id=row.grupo_id,
        razon_social=row.razon_social,
        cuit=row.cuit,
        notas=row.notas,
    )


def rubro(row: m.RubroModel) -> Rubro:
    return Rubro(
        id=row.id,
        empresa_id=row.empresa_id,
        nombre=row.nombre,
        clase=ClaseRubro(row.clase),
        ambito=AmbitoRubro(row.ambito),
        activo=row.activo,
    )


def tipo_pago(row: m.TipoPagoModel) -> TipoPago:
    return TipoPago(
        id=row.id,
        empresa_id=row.empresa_id,
        nombre=row.nombre,
        schema_extra=row.schema_extra or {},
        activo=row.activo,
    )


def refresh(row: m.RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        usuario_id=row.usuario_id,
        token_hash=row.token_hash,
        expira=row.expira,
        revocado=row.revocado,
    )


def archivo(row: m.ArchivoModel) -> Archivo:
    return Archivo(
        id=row.id,
        comprobante_id=row.comprobante_id,
        nombre_original=row.nombre_original,
        mime=row.mime,
        path=row.path,
        sha256=row.sha256,
        size=row.size,
    )


def comprobante(row: m.ComprobanteModel) -> Comprobante:
    from vrf.domain.vos import dinero

    return Comprobante(
        id=row.id,
        empresa_id=row.empresa_id,
        obra_id=row.obra_id,
        proveedor_id=row.proveedor_id,
        usuario_id=row.usuario_id,
        clasificacion=Clasificacion(row.clasificacion),
        rubro_id=row.rubro_id,
        tipo_pago_id=row.tipo_pago_id,
        tipo_afip=TipoAfip(row.tipo_afip),
        punto_venta=row.punto_venta,
        numero=row.numero,
        fecha=row.fecha,
        neto_21=dinero(row.neto_21),
        iva_21=dinero(row.iva_21),
        neto_105=dinero(row.neto_105),
        iva_105=dinero(row.iva_105),
        neto_27=dinero(row.neto_27),
        iva_27=dinero(row.iva_27),
        no_gravado=dinero(row.no_gravado),
        percep_iva=dinero(row.percep_iva),
        percep_iibb=dinero(row.percep_iibb),
        total=dinero(row.total),
        estado_pago=EstadoPago(row.estado_pago),
        cuit_emisor=row.cuit_emisor,
        nota=row.nota,
        extra=row.extra or {},
        comprobado_en=row.comprobado_en,
        comprobado_por=row.comprobado_por,
        anulado_at=row.anulado_at,
        created_at=row.created_at,
        archivo=archivo(row.archivo) if row.archivo else None,
    )
