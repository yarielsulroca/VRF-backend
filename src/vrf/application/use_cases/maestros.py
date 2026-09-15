from uuid import UUID, uuid4

from vrf.domain.entities import Cliente, Empresa, Especialidad, Proveedor, Rubro, TipoPago, Usuario
from vrf.domain.enums import AmbitoRubro, ClaseRubro, Rol, TIPOS_COMPROBANTE
from vrf.domain.exceptions import Conflict, Forbidden, InvalidInput, NotFound
from vrf.domain.ports.repositories import (
    ClienteRepository,
    EmpresaRepository,
    EspecialidadRepository,
    GrupoReader,
    ProveedorRepository,
    RubroRepository,
    TipoPagoRepository,
    UnitOfWork,
    UsuarioRepository,
)
from vrf.domain.ports.security import PasswordHasher
from vrf.domain.vos import Cuit


def _require_admin(actor: Usuario) -> None:
    if actor.rol != Rol.ADMIN:
        raise Forbidden("Solo el admin edita maestros")


class CrearEspecialidad:
    def __init__(self, repo: EspecialidadRepository, grupos: GrupoReader, uow: UnitOfWork) -> None:
        self._repo = repo
        self._grupos = grupos
        self._uow = uow

    def execute(self, actor: Usuario, nombre: str, slug: str) -> Especialidad:
        _require_admin(actor)
        grupo_id, _ = self._grupos.get_unico()
        if self._repo.get_by_slug(grupo_id, slug):
            raise Conflict("Ya existe esa especialidad")
        item = Especialidad(id=uuid4(), grupo_id=grupo_id, nombre=nombre, slug=slug)
        self._repo.add(item)
        self._uow.commit()
        return item


class ListarEspecialidades:
    def __init__(self, repo: EspecialidadRepository, grupos: GrupoReader) -> None:
        self._repo = repo
        self._grupos = grupos

    def execute(self) -> list[Especialidad]:
        grupo_id, _ = self._grupos.get_unico()
        return self._repo.list_by_grupo(grupo_id)


class CrearEmpresa:
    def __init__(
        self,
        empresas: EmpresaRepository,
        especialidades: EspecialidadRepository,
        grupos: GrupoReader,
        uow: UnitOfWork,
    ) -> None:
        self._empresas = empresas
        self._especialidades = especialidades
        self._grupos = grupos
        self._uow = uow

    def execute(
        self, actor: Usuario, razon_social: str, cuit: str, especialidad_id: UUID, activa: bool = True
    ) -> Empresa:
        _require_admin(actor)
        grupo_id, _ = self._grupos.get_unico()
        cuit_n = Cuit(cuit).value
        if self._empresas.get_by_cuit(cuit_n):
            raise Conflict("CUIT de empresa ya cargado")
        if self._especialidades.get(especialidad_id) is None:
            raise NotFound("Especialidad inexistente")
        item = Empresa(
            id=uuid4(),
            grupo_id=grupo_id,
            razon_social=razon_social,
            cuit=cuit_n,
            especialidad_id=especialidad_id,
            activa=activa,
        )
        self._empresas.add(item)
        self._uow.commit()
        return item


class ListarEmpresas:
    def __init__(self, empresas: EmpresaRepository, grupos: GrupoReader) -> None:
        self._empresas = empresas
        self._grupos = grupos

    def execute(self, actor: Usuario) -> list[Empresa]:
        grupo_id, _ = self._grupos.get_unico()
        todas = self._empresas.list_by_grupo(grupo_id)
        if actor.rol == Rol.ADMIN:
            return todas
        permitidas = set(actor.empresa_ids)
        return [e for e in todas if e.id in permitidas]


class CrearCliente:
    def __init__(self, clientes: ClienteRepository, grupos: GrupoReader, uow: UnitOfWork) -> None:
        self._clientes = clientes
        self._grupos = grupos
        self._uow = uow

    def execute(self, actor: Usuario, nombre: str, cuit: str | None) -> Cliente:
        _require_admin(actor)
        grupo_id, _ = self._grupos.get_unico()
        if self._clientes.get_by_nombre(grupo_id, nombre.strip()):
            raise Conflict("Ya existe un cliente con ese nombre")
        cuit_n = Cuit(cuit).value if cuit else None
        item = Cliente(id=uuid4(), grupo_id=grupo_id, nombre=nombre.strip(), cuit=cuit_n)
        self._clientes.add(item)
        self._uow.commit()
        return item


class ListarClientes:
    def __init__(self, clientes: ClienteRepository, grupos: GrupoReader) -> None:
        self._clientes = clientes
        self._grupos = grupos

    def execute(self) -> list[Cliente]:
        grupo_id, _ = self._grupos.get_unico()
        return self._clientes.list_by_grupo(grupo_id)


class CrearProveedor:
    def __init__(self, proveedores: ProveedorRepository, grupos: GrupoReader, uow: UnitOfWork) -> None:
        self._proveedores = proveedores
        self._grupos = grupos
        self._uow = uow

    def execute(self, actor: Usuario, razon_social: str, cuit: str | None, notas: str | None) -> Proveedor:
        _require_admin(actor)
        grupo_id, _ = self._grupos.get_unico()
        cuit_n = Cuit(cuit).value if cuit else None
        if cuit_n and self._proveedores.get_by_cuit(cuit_n):
            raise Conflict("CUIT de proveedor ya cargado")
        item = Proveedor(
            id=uuid4(), grupo_id=grupo_id, razon_social=razon_social, cuit=cuit_n, notas=notas
        )
        self._proveedores.add(item)
        self._uow.commit()
        return item


class ListarProveedores:
    def __init__(self, proveedores: ProveedorRepository, grupos: GrupoReader) -> None:
        self._proveedores = proveedores
        self._grupos = grupos

    def execute(self) -> list[Proveedor]:
        grupo_id, _ = self._grupos.get_unico()
        return self._proveedores.list_by_grupo(grupo_id)


class CrearUsuario:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        empresas: EmpresaRepository,
        grupos: GrupoReader,
        hasher: PasswordHasher,
        uow: UnitOfWork,
    ) -> None:
        self._usuarios = usuarios
        self._empresas = empresas
        self._grupos = grupos
        self._hasher = hasher
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        email: str,
        password: str,
        rol: Rol,
        empresa_ids: list[UUID],
    ) -> Usuario:
        _require_admin(actor)
        email_n = email.strip().lower()
        if self._usuarios.get_by_email(email_n):
            raise Conflict("Email ya registrado")
        if rol == Rol.OPERATIVO and not empresa_ids:
            raise InvalidInput("El operativo necesita al menos una empresa")
        ids = empresa_ids if rol == Rol.OPERATIVO else []
        if ids and len(self._empresas.list_by_ids(ids)) != len(set(ids)):
            raise InvalidInput("Empresa inexistente")
        grupo_id, _ = self._grupos.get_unico()
        item = Usuario(
            id=uuid4(),
            grupo_id=grupo_id,
            email=email_n,
            password_hash=self._hasher.hash(password),
            rol=rol,
            empresa_ids=ids,
        )
        self._usuarios.add(item)
        self._uow.commit()
        return item


class ListarUsuarios:
    def __init__(self, usuarios: UsuarioRepository, grupos: GrupoReader) -> None:
        self._usuarios = usuarios
        self._grupos = grupos

    def execute(self, actor: Usuario) -> list[Usuario]:
        _require_admin(actor)
        grupo_id, _ = self._grupos.get_unico()
        return self._usuarios.list_by_grupo(grupo_id)


class CrearRubro:
    def __init__(self, rubros: RubroRepository, empresas: EmpresaRepository, uow: UnitOfWork) -> None:
        self._rubros = rubros
        self._empresas = empresas
        self._uow = uow

    def execute(
        self, actor: Usuario, empresa_id: UUID, nombre: str, clase: ClaseRubro, ambito: AmbitoRubro
    ) -> Rubro:
        _require_admin(actor)
        if self._empresas.get(empresa_id) is None:
            raise NotFound("Empresa inexistente")
        item = Rubro(id=uuid4(), empresa_id=empresa_id, nombre=nombre, clase=clase, ambito=ambito)
        self._rubros.add(item)
        self._uow.commit()
        return item


class ListarRubros:
    def __init__(self, rubros: RubroRepository) -> None:
        self._rubros = rubros

    def execute(self, empresa_id: UUID) -> list[Rubro]:
        return self._rubros.list_by_empresa(empresa_id)


class CrearTipoPago:
    def __init__(self, tipos: TipoPagoRepository, empresas: EmpresaRepository, uow: UnitOfWork) -> None:
        self._tipos = tipos
        self._empresas = empresas
        self._uow = uow

    def execute(self, actor: Usuario, empresa_id: UUID, nombre: str, schema_extra: dict) -> TipoPago:
        _require_admin(actor)
        if self._empresas.get(empresa_id) is None:
            raise NotFound("Empresa inexistente")
        item = TipoPago(id=uuid4(), empresa_id=empresa_id, nombre=nombre, schema_extra=schema_extra)
        self._tipos.add(item)
        self._uow.commit()
        return item


class ListarTiposPago:
    def __init__(self, tipos: TipoPagoRepository) -> None:
        self._tipos = tipos

    def execute(self, empresa_id: UUID) -> list[TipoPago]:
        return self._tipos.list_by_empresa(empresa_id)


class ListarTiposComprobante:
    def execute(self) -> list[dict]:
        return [{"codigo": codigo.value, "nombre": nombre} for codigo, nombre in TIPOS_COMPROBANTE]


class ObtenerEspecialidad:
    def __init__(self, repo: EspecialidadRepository) -> None:
        self._repo = repo

    def execute(self, especialidad_id: UUID) -> Especialidad:
        item = self._repo.get(especialidad_id)
        if item is None:
            raise NotFound("Especialidad inexistente")
        return item


class ActualizarEspecialidad:
    def __init__(self, repo: EspecialidadRepository, grupos: GrupoReader, uow: UnitOfWork) -> None:
        self._repo = repo
        self._grupos = grupos
        self._uow = uow

    def execute(
        self, actor: Usuario, especialidad_id: UUID, nombre: str | None, slug: str | None
    ) -> Especialidad:
        _require_admin(actor)
        item = self._repo.get(especialidad_id)
        if item is None:
            raise NotFound("Especialidad inexistente")
        if nombre is not None:
            item.nombre = nombre
        if slug is not None:
            grupo_id, _ = self._grupos.get_unico()
            otro = self._repo.get_by_slug(grupo_id, slug)
            if otro and otro.id != item.id:
                raise Conflict("Ya existe esa especialidad")
            item.slug = slug
        self._repo.save(item)
        self._uow.commit()
        return item


class ObtenerEmpresa:
    def __init__(self, empresas: EmpresaRepository) -> None:
        self._empresas = empresas

    def execute(self, actor: Usuario, empresa_id: UUID) -> Empresa:
        item = self._empresas.get(empresa_id)
        if item is None:
            raise NotFound("Empresa inexistente")
        if actor.rol != Rol.ADMIN and empresa_id not in actor.empresa_ids:
            raise Forbidden()
        return item


class ActualizarEmpresa:
    def __init__(
        self,
        empresas: EmpresaRepository,
        especialidades: EspecialidadRepository,
        uow: UnitOfWork,
    ) -> None:
        self._empresas = empresas
        self._especialidades = especialidades
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        empresa_id: UUID,
        razon_social: str | None = None,
        cuit: str | None = None,
        especialidad_id: UUID | None = None,
        activa: bool | None = None,
    ) -> Empresa:
        _require_admin(actor)
        item = self._empresas.get(empresa_id)
        if item is None:
            raise NotFound("Empresa inexistente")
        if razon_social is not None:
            item.razon_social = razon_social
        if cuit is not None:
            cuit_n = Cuit(cuit).value
            otro = self._empresas.get_by_cuit(cuit_n)
            if otro and otro.id != item.id:
                raise Conflict("CUIT de empresa ya cargado")
            item.cuit = cuit_n
        if especialidad_id is not None:
            if self._especialidades.get(especialidad_id) is None:
                raise NotFound("Especialidad inexistente")
            item.especialidad_id = especialidad_id
        if activa is not None:
            item.activa = activa
        self._empresas.save(item)
        self._uow.commit()
        return item


class ObtenerCliente:
    def __init__(self, clientes: ClienteRepository) -> None:
        self._clientes = clientes

    def execute(self, cliente_id: UUID) -> Cliente:
        item = self._clientes.get(cliente_id)
        if item is None:
            raise NotFound("Cliente inexistente")
        return item


class ActualizarCliente:
    def __init__(self, clientes: ClienteRepository, grupos: GrupoReader, uow: UnitOfWork) -> None:
        self._clientes = clientes
        self._grupos = grupos
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        cliente_id: UUID,
        nombre: str | None = None,
        cuit: str | None = None,
        activo: bool | None = None,
        cuit_set: bool = False,
    ) -> Cliente:
        _require_admin(actor)
        item = self._clientes.get(cliente_id)
        if item is None:
            raise NotFound("Cliente inexistente")
        if nombre is not None:
            grupo_id, _ = self._grupos.get_unico()
            otro = self._clientes.get_by_nombre(grupo_id, nombre.strip())
            if otro and otro.id != item.id:
                raise Conflict("Ya existe un cliente con ese nombre")
            item.nombre = nombre.strip()
        if cuit_set:
            item.cuit = Cuit(cuit).value if cuit else None
        if activo is not None:
            item.activo = activo
        self._clientes.save(item)
        self._uow.commit()
        return item


class ObtenerProveedor:
    def __init__(self, proveedores: ProveedorRepository) -> None:
        self._proveedores = proveedores

    def execute(self, proveedor_id: UUID) -> Proveedor:
        item = self._proveedores.get(proveedor_id)
        if item is None:
            raise NotFound("Proveedor inexistente")
        return item


class ActualizarProveedor:
    def __init__(self, proveedores: ProveedorRepository, uow: UnitOfWork) -> None:
        self._proveedores = proveedores
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        proveedor_id: UUID,
        razon_social: str | None = None,
        cuit: str | None = None,
        notas: str | None = None,
        cuit_set: bool = False,
        notas_set: bool = False,
    ) -> Proveedor:
        _require_admin(actor)
        item = self._proveedores.get(proveedor_id)
        if item is None:
            raise NotFound("Proveedor inexistente")
        if razon_social is not None:
            item.razon_social = razon_social
        if cuit_set:
            cuit_n = Cuit(cuit).value if cuit else None
            if cuit_n:
                otro = self._proveedores.get_by_cuit(cuit_n)
                if otro and otro.id != item.id:
                    raise Conflict("CUIT de proveedor ya cargado")
            item.cuit = cuit_n
        if notas_set:
            item.notas = notas
        self._proveedores.save(item)
        self._uow.commit()
        return item


class ObtenerUsuario:
    def __init__(self, usuarios: UsuarioRepository) -> None:
        self._usuarios = usuarios

    def execute(self, actor: Usuario, usuario_id: UUID) -> Usuario:
        _require_admin(actor)
        item = self._usuarios.get(usuario_id)
        if item is None:
            raise NotFound("Usuario inexistente")
        return item


class ActualizarUsuario:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        empresas: EmpresaRepository,
        hasher: PasswordHasher,
        uow: UnitOfWork,
    ) -> None:
        self._usuarios = usuarios
        self._empresas = empresas
        self._hasher = hasher
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        usuario_id: UUID,
        email: str | None = None,
        password: str | None = None,
        rol: Rol | None = None,
        empresa_ids: list[UUID] | None = None,
        activo: bool | None = None,
    ) -> Usuario:
        _require_admin(actor)
        item = self._usuarios.get(usuario_id)
        if item is None:
            raise NotFound("Usuario inexistente")
        if email is not None:
            email_n = email.strip().lower()
            otro = self._usuarios.get_by_email(email_n)
            if otro and otro.id != item.id:
                raise Conflict("Email ya registrado")
            item.email = email_n
        if password:
            item.password_hash = self._hasher.hash(password)
        if rol is not None:
            item.rol = rol
            if rol == Rol.ADMIN:
                item.empresa_ids = []
        ids = empresa_ids if empresa_ids is not None else item.empresa_ids
        if item.rol == Rol.OPERATIVO:
            if not ids:
                raise InvalidInput("El operativo necesita al menos una empresa")
            if len(self._empresas.list_by_ids(ids)) != len(set(ids)):
                raise InvalidInput("Empresa inexistente")
            item.empresa_ids = ids
        else:
            item.empresa_ids = []
        if activo is not None:
            item.activo = activo
        self._usuarios.save(item)
        self._uow.commit()
        return item


class ObtenerRubro:
    def __init__(self, rubros: RubroRepository) -> None:
        self._rubros = rubros

    def execute(self, rubro_id: UUID) -> Rubro:
        item = self._rubros.get(rubro_id)
        if item is None:
            raise NotFound("Rubro inexistente")
        return item


class ActualizarRubro:
    def __init__(self, rubros: RubroRepository, uow: UnitOfWork) -> None:
        self._rubros = rubros
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        rubro_id: UUID,
        nombre: str | None = None,
        clase: ClaseRubro | None = None,
        ambito: AmbitoRubro | None = None,
        activo: bool | None = None,
    ) -> Rubro:
        _require_admin(actor)
        item = self._rubros.get(rubro_id)
        if item is None:
            raise NotFound("Rubro inexistente")
        if nombre is not None:
            item.nombre = nombre
        if clase is not None:
            item.clase = clase
        if ambito is not None:
            item.ambito = ambito
        if activo is not None:
            item.activo = activo
        self._rubros.save(item)
        self._uow.commit()
        return item


class ObtenerTipoPago:
    def __init__(self, tipos: TipoPagoRepository) -> None:
        self._tipos = tipos

    def execute(self, tipo_id: UUID) -> TipoPago:
        item = self._tipos.get(tipo_id)
        if item is None:
            raise NotFound("Tipo de pago inexistente")
        return item


class ActualizarTipoPago:
    def __init__(self, tipos: TipoPagoRepository, uow: UnitOfWork) -> None:
        self._tipos = tipos
        self._uow = uow

    def execute(
        self,
        actor: Usuario,
        tipo_id: UUID,
        nombre: str | None = None,
        schema_extra: dict | None = None,
        activo: bool | None = None,
    ) -> TipoPago:
        _require_admin(actor)
        item = self._tipos.get(tipo_id)
        if item is None:
            raise NotFound("Tipo de pago inexistente")
        if nombre is not None:
            item.nombre = nombre
        if schema_extra is not None:
            item.schema_extra = schema_extra
        if activo is not None:
            item.activo = activo
        self._tipos.save(item)
        self._uow.commit()
        return item
