from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from vrf.adapters.outbound.auth.hasher import BcryptHasher
from vrf.adapters.outbound.auth.jwt import JwtTokens
from vrf.adapters.outbound.clock import SystemClock
from vrf.adapters.outbound.postgres.repos import (
    ClienteRepo,
    ComprobanteRepo,
    EmpresaRepo,
    EspecialidadRepo,
    GrupoRepo,
    ObraRepo,
    ProveedorRepo,
    RefreshTokenRepo,
    RubroRepo,
    TipoPagoRepo,
    UsuarioRepo,
)
from vrf.adapters.outbound.postgres.session import SqlUnitOfWork, get_session
from vrf.adapters.outbound.ocr.adapter import OcrAfipAdapter
from vrf.adapters.outbound.storage.files import FileStorage
from vrf.application.use_cases.auth import Login, Logout, Refresh
from vrf.application.use_cases.maestros import (
    ActualizarCliente,
    ActualizarEmpresa,
    ActualizarEspecialidad,
    ActualizarProveedor,
    ActualizarRubro,
    ActualizarTipoPago,
    ActualizarUsuario,
    CrearCliente,
    CrearEmpresa,
    CrearEspecialidad,
    CrearProveedor,
    CrearRubro,
    CrearTipoPago,
    CrearUsuario,
    ListarClientes,
    ListarEmpresas,
    ListarEspecialidades,
    ListarProveedores,
    ListarRubros,
    ListarTiposComprobante,
    ListarTiposPago,
    ListarUsuarios,
    ObtenerCliente,
    ObtenerEmpresa,
    ObtenerEspecialidad,
    ObtenerProveedor,
    ObtenerRubro,
    ObtenerTipoPago,
    ObtenerUsuario,
)
from vrf.application.use_cases.ocr import PreviewOcr
from vrf.application.use_cases.consultas import (
    ConsultarCostosObra,
    ConsultarDashboard,
    ExportarLibroIva,
    ListarCostos,
)
from vrf.application.use_cases.comprobantes import (
    ActualizarComprobante,
    CambiarEstado,
    CrearComprobante,
    ListarComprobantes,
    ObtenerComprobante,
    ReemplazarArchivo,
    ServirOriginal,
)
from vrf.application.use_cases.obras import (
    ActualizarObra,
    AgregarParticipacion,
    CrearObra,
    ListarObras,
    ObtenerObra,
    QuitarParticipacion,
)
from vrf.application.use_cases.planilla import ConfirmarImportacion, ExportarRegistros, PreviaImportacion
from vrf.adapters.outbound.planilla.xlsx import OpenpyxlEscritor
from vrf.config import settings
from vrf.domain.entities import Usuario
from vrf.domain.exceptions import Unauthorized


def session_dep(session: Session = Depends(get_session)) -> Session:
    return session


@dataclass
class Container:
    session: Session

    def __post_init__(self) -> None:
        s = self.session
        self.uow = SqlUnitOfWork(s)
        self.hasher = BcryptHasher()
        self.jwt = JwtTokens(settings.jwt_secret, settings.jwt_refresh_secret)
        self.clock = SystemClock()
        self.especialidades = EspecialidadRepo(s)
        self.empresas = EmpresaRepo(s)
        self.clientes = ClienteRepo(s)
        self.obras = ObraRepo(s)
        self.usuarios = UsuarioRepo(s)
        self.proveedores = ProveedorRepo(s)
        self.rubros = RubroRepo(s)
        self.tipos = TipoPagoRepo(s)
        self.refresh_tokens = RefreshTokenRepo(s)
        self.grupos = GrupoRepo(s)
        self.comprobantes = ComprobanteRepo(s)
        self.storage = FileStorage(settings.storage_path)
        self.ocr = OcrAfipAdapter()


def container(session: Session = Depends(session_dep)) -> Container:
    return Container(session)


def current_user(
    authorization: Annotated[str | None, Header()] = None,
    c: Container = Depends(container),
) -> Usuario:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized()
    user_id, _rol = c.jwt.parse_access(authorization.split(" ", 1)[1])
    user = c.usuarios.get(user_id)
    if user is None or not user.activo:
        raise Unauthorized()
    return user


def login_uc(c: Container = Depends(container)) -> Login:
    return Login(c.usuarios, c.refresh_tokens, c.hasher, c.jwt, c.clock, c.uow)


def refresh_uc(c: Container = Depends(container)) -> Refresh:
    return Refresh(c.usuarios, c.refresh_tokens, c.jwt, c.clock, c.uow)


def logout_uc(c: Container = Depends(container)) -> Logout:
    return Logout(c.refresh_tokens, c.jwt, c.uow)


def crear_especialidad_uc(c: Container = Depends(container)) -> CrearEspecialidad:
    return CrearEspecialidad(c.especialidades, c.grupos, c.uow)


def listar_especialidades_uc(c: Container = Depends(container)) -> ListarEspecialidades:
    return ListarEspecialidades(c.especialidades, c.grupos)


def crear_empresa_uc(c: Container = Depends(container)) -> CrearEmpresa:
    return CrearEmpresa(c.empresas, c.especialidades, c.grupos, c.uow)


def listar_empresas_uc(c: Container = Depends(container)) -> ListarEmpresas:
    return ListarEmpresas(c.empresas, c.grupos)


def crear_cliente_uc(c: Container = Depends(container)) -> CrearCliente:
    return CrearCliente(c.clientes, c.grupos, c.uow)


def listar_clientes_uc(c: Container = Depends(container)) -> ListarClientes:
    return ListarClientes(c.clientes, c.grupos)


def crear_proveedor_uc(c: Container = Depends(container)) -> CrearProveedor:
    return CrearProveedor(c.proveedores, c.grupos, c.uow)


def listar_proveedores_uc(c: Container = Depends(container)) -> ListarProveedores:
    return ListarProveedores(c.proveedores, c.grupos)


def crear_usuario_uc(c: Container = Depends(container)) -> CrearUsuario:
    return CrearUsuario(c.usuarios, c.empresas, c.grupos, c.hasher, c.uow)


def listar_usuarios_uc(c: Container = Depends(container)) -> ListarUsuarios:
    return ListarUsuarios(c.usuarios, c.grupos)


def crear_rubro_uc(c: Container = Depends(container)) -> CrearRubro:
    return CrearRubro(c.rubros, c.empresas, c.uow)


def listar_rubros_uc(c: Container = Depends(container)) -> ListarRubros:
    return ListarRubros(c.rubros)


def crear_tipo_uc(c: Container = Depends(container)) -> CrearTipoPago:
    return CrearTipoPago(c.tipos, c.empresas, c.uow)


def listar_tipos_uc(c: Container = Depends(container)) -> ListarTiposPago:
    return ListarTiposPago(c.tipos)


def crear_obra_uc(c: Container = Depends(container)) -> CrearObra:
    return CrearObra(c.obras, c.clientes, c.empresas, c.uow)


def listar_obras_uc(c: Container = Depends(container)) -> ListarObras:
    return ListarObras(c.obras, c.clientes)


def obtener_obra_uc(c: Container = Depends(container)) -> ObtenerObra:
    return ObtenerObra(c.obras)


def quitar_part_uc(c: Container = Depends(container)) -> QuitarParticipacion:
    return QuitarParticipacion(c.obras, c.uow)


def agregar_part_uc(c: Container = Depends(container)) -> AgregarParticipacion:
    return AgregarParticipacion(c.obras, c.empresas, c.clientes, c.uow)


def actualizar_obra_uc(c: Container = Depends(container)) -> ActualizarObra:
    return ActualizarObra(c.obras, c.uow)


def obtener_especialidad_uc(c: Container = Depends(container)) -> ObtenerEspecialidad:
    return ObtenerEspecialidad(c.especialidades)


def actualizar_especialidad_uc(c: Container = Depends(container)) -> ActualizarEspecialidad:
    return ActualizarEspecialidad(c.especialidades, c.grupos, c.uow)


def obtener_empresa_uc(c: Container = Depends(container)) -> ObtenerEmpresa:
    return ObtenerEmpresa(c.empresas)


def actualizar_empresa_uc(c: Container = Depends(container)) -> ActualizarEmpresa:
    return ActualizarEmpresa(c.empresas, c.especialidades, c.uow)


def obtener_cliente_uc(c: Container = Depends(container)) -> ObtenerCliente:
    return ObtenerCliente(c.clientes)


def actualizar_cliente_uc(c: Container = Depends(container)) -> ActualizarCliente:
    return ActualizarCliente(c.clientes, c.grupos, c.uow)


def obtener_proveedor_uc(c: Container = Depends(container)) -> ObtenerProveedor:
    return ObtenerProveedor(c.proveedores)


def actualizar_proveedor_uc(c: Container = Depends(container)) -> ActualizarProveedor:
    return ActualizarProveedor(c.proveedores, c.uow)


def obtener_usuario_uc(c: Container = Depends(container)) -> ObtenerUsuario:
    return ObtenerUsuario(c.usuarios)


def actualizar_usuario_uc(c: Container = Depends(container)) -> ActualizarUsuario:
    return ActualizarUsuario(c.usuarios, c.empresas, c.hasher, c.uow)


def obtener_rubro_uc(c: Container = Depends(container)) -> ObtenerRubro:
    return ObtenerRubro(c.rubros)


def actualizar_rubro_uc(c: Container = Depends(container)) -> ActualizarRubro:
    return ActualizarRubro(c.rubros, c.uow)


def obtener_tipo_uc(c: Container = Depends(container)) -> ObtenerTipoPago:
    return ObtenerTipoPago(c.tipos)


def actualizar_tipo_uc(c: Container = Depends(container)) -> ActualizarTipoPago:
    return ActualizarTipoPago(c.tipos, c.uow)


def listar_tipos_comprobante_uc() -> ListarTiposComprobante:
    return ListarTiposComprobante()


def crear_comprobante_uc(c: Container = Depends(container)) -> CrearComprobante:
    return CrearComprobante(
        c.comprobantes,
        c.empresas,
        c.obras,
        c.proveedores,
        c.rubros,
        c.tipos,
        c.usuarios,
        c.storage,
        c.clock,
        c.uow,
    )


def listar_comprobantes_uc(c: Container = Depends(container)) -> ListarComprobantes:
    return ListarComprobantes(c.comprobantes)


def exportar_registros_uc(c: Container = Depends(container)) -> ExportarRegistros:
    return ExportarRegistros(
        ListarComprobantes(c.comprobantes),
        OpenpyxlEscritor(),
        c.obras,
        c.proveedores,
        c.rubros,
        c.tipos,
        c.clientes,
    )


def previa_importacion_uc(c: Container = Depends(container)) -> PreviaImportacion:
    return PreviaImportacion(
        c.comprobantes,
        c.proveedores,
        c.rubros,
        c.tipos,
        c.obras,
        settings.jwt_secret,
    )


def confirmar_importacion_uc(c: Container = Depends(container)) -> ConfirmarImportacion:
    previa = previa_importacion_uc(c)
    crear = crear_comprobante_uc(c)
    return ConfirmarImportacion(previa, crear, c.proveedores, c.rubros, c.uow, settings.jwt_secret)


def obtener_comprobante_uc(c: Container = Depends(container)) -> ObtenerComprobante:
    return ObtenerComprobante(c.comprobantes)


def actualizar_comprobante_uc(c: Container = Depends(container)) -> ActualizarComprobante:
    return ActualizarComprobante(c.comprobantes, c.obras, c.rubros, c.tipos, c.uow)


def reemplazar_archivo_uc(c: Container = Depends(container)) -> ReemplazarArchivo:
    return ReemplazarArchivo(c.comprobantes, c.storage, c.uow)


def cambiar_estado_uc(c: Container = Depends(container)) -> CambiarEstado:
    return CambiarEstado(c.comprobantes, c.clock, c.uow)


def servir_original_uc(c: Container = Depends(container)) -> ServirOriginal:
    return ServirOriginal(c.comprobantes, c.storage)


def preview_ocr_uc(c: Container = Depends(container)) -> PreviewOcr:
    return PreviewOcr(c.ocr, c.proveedores, c.grupos, c.uow)


def dashboard_uc(c: Container = Depends(container)) -> ConsultarDashboard:
    return ConsultarDashboard(c.comprobantes, c.empresas, c.obras, c.proveedores, c.grupos)


def costos_obra_uc(c: Container = Depends(container)) -> ConsultarCostosObra:
    return ConsultarCostosObra(
        c.comprobantes, c.obras, c.clientes, c.empresas, c.proveedores, c.rubros, c.tipos
    )


def listar_costos_uc(c: Container = Depends(container)) -> ListarCostos:
    return ListarCostos(c.comprobantes, c.obras, c.clientes, c.empresas, c.grupos)


def exportar_libro_iva_uc(c: Container = Depends(container)) -> ExportarLibroIva:
    return ExportarLibroIva(
        c.comprobantes, c.empresas, c.obras, c.proveedores, c.rubros, c.tipos
    )
