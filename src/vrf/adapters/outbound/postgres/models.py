from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GrupoModel(Base):
    __tablename__ = "grupos"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre: Mapped[str] = mapped_column(String(200))
    dueno: Mapped[str] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class EspecialidadModel(Base):
    __tablename__ = "especialidades"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    grupo_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("grupos.id"))
    nombre: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80))
    __table_args__ = (UniqueConstraint("grupo_id", "slug"),)


class EmpresaModel(Base):
    __tablename__ = "empresas"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    grupo_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("grupos.id"))
    razon_social: Mapped[str] = mapped_column(String(200))
    cuit: Mapped[str] = mapped_column(String(11), unique=True)
    especialidad_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("especialidades.id"))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class ClienteModel(Base):
    __tablename__ = "clientes"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    grupo_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("grupos.id"))
    nombre: Mapped[str] = mapped_column(String(200))
    cuit: Mapped[str | None] = mapped_column(String(11), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("grupo_id", "nombre"),)


class ObraEmpresaModel(Base):
    __tablename__ = "obra_empresas"
    obra_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("obras.id"), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id"), primary_key=True
    )


class ObraModel(Base):
    __tablename__ = "obras"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    cliente_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id"))
    nombre: Mapped[str] = mapped_column(String(200))
    direccion: Mapped[str] = mapped_column(String(300), default="")
    tipo_trabajo: Mapped[str] = mapped_column(String(30))
    origen_mantenimiento: Mapped[str | None] = mapped_column(String(40), nullable=True)
    obra_origen_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("obras.id"), nullable=True
    )
    origen_terceros_nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    sustituye: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas_equipo: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="abierta")
    participantes: Mapped[list[ObraEmpresaModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class UsuarioEmpresaModel(Base):
    __tablename__ = "usuario_empresas"
    usuario_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True
    )
    empresa_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id"), primary_key=True
    )


class UsuarioModel(Base):
    __tablename__ = "usuarios"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    grupo_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("grupos.id"))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    empresas: Mapped[list[UsuarioEmpresaModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class ProveedorModel(Base):
    __tablename__ = "proveedores"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    grupo_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("grupos.id"))
    razon_social: Mapped[str] = mapped_column(String(200))
    cuit: Mapped[str | None] = mapped_column(String(11), unique=True, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


class RubroModel(Base):
    __tablename__ = "rubros"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    empresa_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    nombre: Mapped[str] = mapped_column(String(200))
    clase: Mapped[str] = mapped_column(String(30))
    ambito: Mapped[str] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class TipoPagoModel(Base):
    __tablename__ = "tipos_pago"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    empresa_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    nombre: Mapped[str] = mapped_column(String(200))
    schema_extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocado: Mapped[bool] = mapped_column(Boolean, default=False)


class ComprobanteModel(Base):
    __tablename__ = "comprobantes"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    empresa_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    obra_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("obras.id"), nullable=True)
    proveedor_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("proveedores.id"), nullable=True
    )
    usuario_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    clasificacion: Mapped[str] = mapped_column(String(20))
    rubro_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rubros.id"), nullable=True)
    tipo_pago_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tipos_pago.id"), nullable=True
    )
    tipo_afip: Mapped[str] = mapped_column(String(10))
    punto_venta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_comprobante: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fecha: Mapped[date] = mapped_column(Date)
    neto_21: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    iva_21: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    neto_105: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    iva_105: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    neto_27: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    iva_27: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    no_gravado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    percep_iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    percep_iibb: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    estado_pago: Mapped[str] = mapped_column(String(30))
    cuit_emisor: Mapped[str | None] = mapped_column(String(11), nullable=True)
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    comprobado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    comprobado_por: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archivo: Mapped["ArchivoModel | None"] = relationship(
        back_populates="comprobante", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    __table_args__ = (
        Index("ix_comp_empresa_fecha", "empresa_id", "fecha"),
        Index("ix_comp_obra_fecha", "obra_id", "fecha"),
        Index("ix_comp_estado", "estado_pago"),
        Index(
            "uq_comprobante_afip",
            "cuit_emisor",
            "tipo_afip",
            "punto_venta",
            "numero",
            unique=True,
            postgresql_where=text(
                "numero IS NOT NULL AND punto_venta IS NOT NULL AND tipo_afip IN ('A','B','C')"
            ),
        ),
    )


class ArchivoModel(Base):
    __tablename__ = "archivos"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    comprobante_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comprobantes.id"), unique=True
    )
    nombre_original: Mapped[str] = mapped_column(String(300))
    mime: Mapped[str] = mapped_column(String(120))
    path: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    comprobante: Mapped[ComprobanteModel] = relationship(back_populates="archivo")
