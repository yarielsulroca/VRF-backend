from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

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


@dataclass
class Especialidad:
    id: UUID
    grupo_id: UUID
    nombre: str
    slug: str


@dataclass
class Empresa:
    id: UUID
    grupo_id: UUID
    razon_social: str
    cuit: str
    especialidad_id: UUID
    activa: bool = True


@dataclass
class Cliente:
    id: UUID
    grupo_id: UUID
    nombre: str
    cuit: str | None
    activo: bool = True


@dataclass
class Obra:
    id: UUID
    cliente_id: UUID
    nombre: str
    direccion: str
    tipo_trabajo: TipoTrabajo
    estado: EstadoObra
    empresa_ids: list[UUID]
    origen_mantenimiento: OrigenMantenimiento | None = None
    obra_origen_id: UUID | None = None
    origen_terceros_nota: str | None = None
    sustituye: str | None = None
    notas_equipo: str | None = None


@dataclass
class Usuario:
    id: UUID
    grupo_id: UUID
    email: str
    password_hash: str
    rol: Rol
    activo: bool = True
    empresa_ids: list[UUID] = field(default_factory=list)


@dataclass
class Proveedor:
    id: UUID
    grupo_id: UUID
    razon_social: str
    cuit: str | None
    notas: str | None = None


@dataclass
class Rubro:
    id: UUID
    empresa_id: UUID
    nombre: str
    clase: ClaseRubro
    ambito: AmbitoRubro
    activo: bool = True


@dataclass
class TipoPago:
    id: UUID
    empresa_id: UUID
    nombre: str
    schema_extra: dict
    activo: bool = True


@dataclass
class RefreshToken:
    id: UUID
    usuario_id: UUID
    token_hash: str
    expira: datetime
    revocado: bool = False


@dataclass
class Archivo:
    id: UUID
    comprobante_id: UUID
    nombre_original: str
    mime: str
    path: str
    sha256: str
    size: int


@dataclass
class Comprobante:
    id: UUID
    empresa_id: UUID
    obra_id: UUID | None
    proveedor_id: UUID | None
    usuario_id: UUID
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
    estado_pago: EstadoPago
    cuit_emisor: str | None
    numero_comprobante: str | None = None
    nota: str | None = None
    extra: dict = field(default_factory=dict)
    comprobado_en: datetime | None = None
    comprobado_por: UUID | None = None
    anulado_at: datetime | None = None
    created_at: datetime | None = None
    archivo: Archivo | None = None
