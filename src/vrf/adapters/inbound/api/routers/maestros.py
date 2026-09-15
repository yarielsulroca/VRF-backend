from uuid import UUID

from fastapi import APIRouter, Depends

from vrf.adapters.inbound.api.deps import (
    actualizar_cliente_uc,
    actualizar_empresa_uc,
    actualizar_especialidad_uc,
    actualizar_proveedor_uc,
    actualizar_rubro_uc,
    actualizar_tipo_uc,
    actualizar_usuario_uc,
    crear_cliente_uc,
    crear_empresa_uc,
    crear_especialidad_uc,
    crear_proveedor_uc,
    crear_rubro_uc,
    crear_tipo_uc,
    crear_usuario_uc,
    current_user,
    listar_clientes_uc,
    listar_empresas_uc,
    listar_especialidades_uc,
    listar_proveedores_uc,
    listar_rubros_uc,
    listar_tipos_comprobante_uc,
    listar_tipos_uc,
    listar_usuarios_uc,
    obtener_cliente_uc,
    obtener_empresa_uc,
    obtener_especialidad_uc,
    obtener_proveedor_uc,
    obtener_rubro_uc,
    obtener_tipo_uc,
    obtener_usuario_uc,
)
from vrf.adapters.inbound.api.schemas import (
    ClienteIn,
    ClientePatch,
    EmpresaIn,
    EmpresaPatch,
    EspecialidadIn,
    EspecialidadPatch,
    ProveedorIn,
    ProveedorPatch,
    RubroIn,
    RubroPatch,
    TipoPagoIn,
    TipoPagoPatch,
    UsuarioIn,
    UsuarioPatch,
)
from vrf.adapters.inbound.api.serialize import dump
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
from vrf.domain.entities import Usuario
from vrf.domain.enums import AmbitoRubro, ClaseRubro, Rol

router = APIRouter(tags=["maestros"])


@router.get("/tipos-comprobante")
def get_tipos_comprobante(
    _actor: Usuario = Depends(current_user),
    uc: ListarTiposComprobante = Depends(listar_tipos_comprobante_uc),
) -> list:
    return uc.execute()


@router.get("/especialidades")
def get_especialidades(
    _actor: Usuario = Depends(current_user),
    uc: ListarEspecialidades = Depends(listar_especialidades_uc),
) -> list:
    return [dump(x) for x in uc.execute()]


@router.get("/especialidades/{especialidad_id}")
def get_especialidad(
    especialidad_id: UUID,
    _actor: Usuario = Depends(current_user),
    uc: ObtenerEspecialidad = Depends(obtener_especialidad_uc),
) -> dict:
    return dump(uc.execute(especialidad_id))


@router.post("/especialidades")
def post_especialidad(
    body: EspecialidadIn,
    actor: Usuario = Depends(current_user),
    uc: CrearEspecialidad = Depends(crear_especialidad_uc),
) -> dict:
    return dump(uc.execute(actor, body.nombre, body.slug))


@router.patch("/especialidades/{especialidad_id}")
def patch_especialidad(
    especialidad_id: UUID,
    body: EspecialidadPatch,
    actor: Usuario = Depends(current_user),
    uc: ActualizarEspecialidad = Depends(actualizar_especialidad_uc),
) -> dict:
    return dump(uc.execute(actor, especialidad_id, body.nombre, body.slug))


@router.get("/empresas")
def get_empresas(
    actor: Usuario = Depends(current_user), uc: ListarEmpresas = Depends(listar_empresas_uc)
) -> list:
    return [dump(x) for x in uc.execute(actor)]


@router.get("/empresas/{empresa_id}")
def get_empresa(
    empresa_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ObtenerEmpresa = Depends(obtener_empresa_uc),
) -> dict:
    return dump(uc.execute(actor, empresa_id))


@router.post("/empresas")
def post_empresa(
    body: EmpresaIn,
    actor: Usuario = Depends(current_user),
    uc: CrearEmpresa = Depends(crear_empresa_uc),
) -> dict:
    return dump(uc.execute(actor, body.razon_social, body.cuit, body.especialidad_id, body.activa))


@router.patch("/empresas/{empresa_id}")
def patch_empresa(
    empresa_id: UUID,
    body: EmpresaPatch,
    actor: Usuario = Depends(current_user),
    uc: ActualizarEmpresa = Depends(actualizar_empresa_uc),
) -> dict:
    return dump(
        uc.execute(
            actor,
            empresa_id,
            body.razon_social,
            body.cuit,
            body.especialidad_id,
            body.activa,
        )
    )


@router.delete("/empresas/{empresa_id}")
def delete_empresa(
    empresa_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ActualizarEmpresa = Depends(actualizar_empresa_uc),
) -> dict:
    return dump(uc.execute(actor, empresa_id, activa=False))


@router.get("/clientes")
def get_clientes(
    actor: Usuario = Depends(current_user), uc: ListarClientes = Depends(listar_clientes_uc)
) -> list:
    return [dump(x) for x in uc.execute()]


@router.get("/clientes/{cliente_id}")
def get_cliente(
    cliente_id: UUID,
    _actor: Usuario = Depends(current_user),
    uc: ObtenerCliente = Depends(obtener_cliente_uc),
) -> dict:
    return dump(uc.execute(cliente_id))


@router.post("/clientes")
def post_cliente(
    body: ClienteIn,
    actor: Usuario = Depends(current_user),
    uc: CrearCliente = Depends(crear_cliente_uc),
) -> dict:
    return dump(uc.execute(actor, body.nombre, body.cuit))


@router.patch("/clientes/{cliente_id}")
def patch_cliente(
    cliente_id: UUID,
    body: ClientePatch,
    actor: Usuario = Depends(current_user),
    uc: ActualizarCliente = Depends(actualizar_cliente_uc),
) -> dict:
    return dump(
        uc.execute(
            actor,
            cliente_id,
            body.nombre,
            body.cuit,
            body.activo,
            cuit_set="cuit" in body.model_fields_set,
        )
    )


@router.delete("/clientes/{cliente_id}")
def delete_cliente(
    cliente_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ActualizarCliente = Depends(actualizar_cliente_uc),
) -> dict:
    return dump(uc.execute(actor, cliente_id, activo=False))


@router.get("/proveedores")
def get_proveedores(
    actor: Usuario = Depends(current_user), uc: ListarProveedores = Depends(listar_proveedores_uc)
) -> list:
    return [dump(x) for x in uc.execute()]


@router.get("/proveedores/{proveedor_id}")
def get_proveedor(
    proveedor_id: UUID,
    _actor: Usuario = Depends(current_user),
    uc: ObtenerProveedor = Depends(obtener_proveedor_uc),
) -> dict:
    return dump(uc.execute(proveedor_id))


@router.post("/proveedores")
def post_proveedor(
    body: ProveedorIn,
    actor: Usuario = Depends(current_user),
    uc: CrearProveedor = Depends(crear_proveedor_uc),
) -> dict:
    return dump(uc.execute(actor, body.razon_social, body.cuit, body.notas))


@router.patch("/proveedores/{proveedor_id}")
def patch_proveedor(
    proveedor_id: UUID,
    body: ProveedorPatch,
    actor: Usuario = Depends(current_user),
    uc: ActualizarProveedor = Depends(actualizar_proveedor_uc),
) -> dict:
    return dump(
        uc.execute(
            actor,
            proveedor_id,
            body.razon_social,
            body.cuit,
            body.notas,
            cuit_set="cuit" in body.model_fields_set,
            notas_set="notas" in body.model_fields_set,
        )
    )


@router.get("/usuarios")
def get_usuarios(
    actor: Usuario = Depends(current_user), uc: ListarUsuarios = Depends(listar_usuarios_uc)
) -> list:
    return [dump(x) for x in uc.execute(actor)]


@router.get("/usuarios/{usuario_id}")
def get_usuario(
    usuario_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ObtenerUsuario = Depends(obtener_usuario_uc),
) -> dict:
    return dump(uc.execute(actor, usuario_id))


@router.post("/usuarios")
def post_usuario(
    body: UsuarioIn,
    actor: Usuario = Depends(current_user),
    uc: CrearUsuario = Depends(crear_usuario_uc),
) -> dict:
    return dump(uc.execute(actor, body.email, body.password, Rol(body.rol), body.empresa_ids))


@router.patch("/usuarios/{usuario_id}")
def patch_usuario(
    usuario_id: UUID,
    body: UsuarioPatch,
    actor: Usuario = Depends(current_user),
    uc: ActualizarUsuario = Depends(actualizar_usuario_uc),
) -> dict:
    rol = Rol(body.rol) if body.rol else None
    return dump(
        uc.execute(actor, usuario_id, body.email, body.password, rol, body.empresa_ids, body.activo)
    )


@router.delete("/usuarios/{usuario_id}")
def delete_usuario(
    usuario_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ActualizarUsuario = Depends(actualizar_usuario_uc),
) -> dict:
    return dump(uc.execute(actor, usuario_id, activo=False))


@router.get("/rubros")
def get_rubros(
    empresa_id: UUID,
    _actor: Usuario = Depends(current_user),
    uc: ListarRubros = Depends(listar_rubros_uc),
) -> list:
    return [dump(x) for x in uc.execute(empresa_id)]


@router.get("/rubros/{rubro_id}")
def get_rubro(
    rubro_id: UUID,
    _actor: Usuario = Depends(current_user),
    uc: ObtenerRubro = Depends(obtener_rubro_uc),
) -> dict:
    return dump(uc.execute(rubro_id))


@router.post("/rubros")
def post_rubro(
    body: RubroIn,
    actor: Usuario = Depends(current_user),
    uc: CrearRubro = Depends(crear_rubro_uc),
) -> dict:
    return dump(
        uc.execute(actor, body.empresa_id, body.nombre, ClaseRubro(body.clase), AmbitoRubro(body.ambito))
    )


@router.patch("/rubros/{rubro_id}")
def patch_rubro(
    rubro_id: UUID,
    body: RubroPatch,
    actor: Usuario = Depends(current_user),
    uc: ActualizarRubro = Depends(actualizar_rubro_uc),
) -> dict:
    clase = ClaseRubro(body.clase) if body.clase else None
    ambito = AmbitoRubro(body.ambito) if body.ambito else None
    return dump(uc.execute(actor, rubro_id, body.nombre, clase, ambito, body.activo))


@router.delete("/rubros/{rubro_id}")
def delete_rubro(
    rubro_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ActualizarRubro = Depends(actualizar_rubro_uc),
) -> dict:
    return dump(uc.execute(actor, rubro_id, activo=False))


@router.get("/tipos-pago")
def get_tipos(
    empresa_id: UUID,
    _actor: Usuario = Depends(current_user),
    uc: ListarTiposPago = Depends(listar_tipos_uc),
) -> list:
    return [dump(x) for x in uc.execute(empresa_id)]


@router.get("/tipos-pago/{tipo_id}")
def get_tipo(
    tipo_id: UUID,
    _actor: Usuario = Depends(current_user),
    uc: ObtenerTipoPago = Depends(obtener_tipo_uc),
) -> dict:
    return dump(uc.execute(tipo_id))


@router.post("/tipos-pago")
def post_tipo(
    body: TipoPagoIn,
    actor: Usuario = Depends(current_user),
    uc: CrearTipoPago = Depends(crear_tipo_uc),
) -> dict:
    return dump(uc.execute(actor, body.empresa_id, body.nombre, body.schema_extra))


@router.patch("/tipos-pago/{tipo_id}")
def patch_tipo(
    tipo_id: UUID,
    body: TipoPagoPatch,
    actor: Usuario = Depends(current_user),
    uc: ActualizarTipoPago = Depends(actualizar_tipo_uc),
) -> dict:
    return dump(uc.execute(actor, tipo_id, body.nombre, body.schema_extra, body.activo))


@router.delete("/tipos-pago/{tipo_id}")
def delete_tipo(
    tipo_id: UUID,
    actor: Usuario = Depends(current_user),
    uc: ActualizarTipoPago = Depends(actualizar_tipo_uc),
) -> dict:
    return dump(uc.execute(actor, tipo_id, activo=False))
