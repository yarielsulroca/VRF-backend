from uuid import UUID

from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    rol: str | None = None
    usuario_id: str | None = None


class EspecialidadIn(BaseModel):
    nombre: str
    slug: str


class EmpresaIn(BaseModel):
    razon_social: str
    cuit: str
    especialidad_id: UUID
    activa: bool = True


class ClienteIn(BaseModel):
    nombre: str
    cuit: str | None = None


class ProveedorIn(BaseModel):
    razon_social: str
    cuit: str | None = None
    notas: str | None = None


class UsuarioIn(BaseModel):
    email: str
    password: str
    rol: str
    empresa_ids: list[UUID] = Field(default_factory=list)


class RubroIn(BaseModel):
    empresa_id: UUID
    nombre: str
    clase: str = "compra_costo"
    ambito: str = "ambos"


class TipoPagoIn(BaseModel):
    empresa_id: UUID
    nombre: str
    schema_extra: dict = Field(default_factory=dict)


class ObraIn(BaseModel):
    cliente_id: UUID
    nombre: str
    direccion: str = ""
    tipo_trabajo: str
    empresa_ids: list[UUID]
    origen_mantenimiento: str | None = None
    obra_origen_id: UUID | None = None
    origen_terceros_nota: str | None = None
    sustituye: str | None = None
    notas_equipo: str | None = None


class ParticipacionIn(BaseModel):
    empresa_id: UUID


class ArchivoIn(BaseModel):
    nombre_original: str
    mime: str
    size: int


class ArchivoOut(BaseModel):
    nombre_original: str
    mime: str
    path: str
    sha256: str
    size: int


class EspecialidadPatch(BaseModel):
    nombre: str | None = None
    slug: str | None = None


class EmpresaPatch(BaseModel):
    razon_social: str | None = None
    cuit: str | None = None
    especialidad_id: UUID | None = None
    activa: bool | None = None


class ClientePatch(BaseModel):
    nombre: str | None = None
    cuit: str | None = None
    activo: bool | None = None


class ProveedorPatch(BaseModel):
    razon_social: str | None = None
    cuit: str | None = None
    notas: str | None = None


class UsuarioPatch(BaseModel):
    email: str | None = None
    password: str | None = None
    rol: str | None = None
    empresa_ids: list[UUID] | None = None
    activo: bool | None = None


class RubroPatch(BaseModel):
    nombre: str | None = None
    clase: str | None = None
    ambito: str | None = None
    activo: bool | None = None


class TipoPagoPatch(BaseModel):
    nombre: str | None = None
    schema_extra: dict | None = None
    activo: bool | None = None


class ObraPatch(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    estado: str | None = None
    notas_equipo: str | None = None


class ComprobanteAltaIn(BaseModel):
    empresa_id: UUID
    obra_id: UUID | None = None
    proveedor_id: UUID | None = None
    clasificacion: str
    rubro_id: UUID | None = None
    tipo_pago_id: UUID | None = None
    tipo_afip: str
    punto_venta: int | None = None
    numero: int | None = None
    numero_comprobante: str | None = None
    fecha: date
    neto_21: Decimal = Decimal("0")
    iva_21: Decimal = Decimal("0")
    neto_105: Decimal = Decimal("0")
    iva_105: Decimal = Decimal("0")
    neto_27: Decimal = Decimal("0")
    iva_27: Decimal = Decimal("0")
    no_gravado: Decimal = Decimal("0")
    percep_iva: Decimal = Decimal("0")
    percep_iibb: Decimal = Decimal("0")
    total: Decimal
    ya_pagada: bool = False
    nota: str | None = None
    extra: dict = Field(default_factory=dict)


class ComprobantePatch(BaseModel):
    """Solo organización / clasificación. Datos propios de la factura son inmutables."""

    obra_id: UUID | None = None
    rubro_id: UUID | None = None
    tipo_pago_id: UUID | None = None
    clasificacion: str | None = None
    clear_obra: bool = False


class ImportarConfirmarIn(BaseModel):
    token: str
