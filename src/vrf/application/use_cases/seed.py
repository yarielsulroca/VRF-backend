from uuid import uuid4

from vrf.domain.entities import Cliente, Empresa, Especialidad, Obra, Rubro, TipoPago, Usuario
from vrf.domain.enums import AmbitoRubro, ClaseRubro, EstadoObra, Rol, TipoTrabajo
from vrf.domain.ports.repositories import (
    ClienteRepository,
    EmpresaRepository,
    EspecialidadRepository,
    GrupoReader,
    ObraRepository,
    RubroRepository,
    TipoPagoRepository,
    UnitOfWork,
    UsuarioRepository,
)
from vrf.domain.ports.security import PasswordHasher
from vrf.domain.vos import Cuit

RUBROS_VRF = [
    "Cañería",
    "Conductos",
    "Display baja silueta",
    "Ferretería",
    "Filtros",
    "Flexibles",
    "Refrigerante",
    "Rejas",
    "Ventiladores",
    "Andamios",
]
RUBROS_ELEC = ["Cables", "Tableros", "Caños eléctricos"]
TIPOS_PAGO = [
    ("Eléctrico", {}),
    ("Jefe de obra", {}),
    ("Mensajería", {"vehiculo": "string", "elementos": "array"}),
    ("Flete/transporte", {}),
    ("Técnico mantenimiento", {}),
    ("Mano de obra cañista", {}),
    ("Mano de obra conductos", {}),
]
CUIT_VRF = "33-71117492-9"
CUIT_ELEC = "30712345620"


class SeedInicial:
    def __init__(
        self,
        grupos: GrupoReader,
        especialidades: EspecialidadRepository,
        empresas: EmpresaRepository,
        usuarios: UsuarioRepository,
        rubros: RubroRepository,
        tipos: TipoPagoRepository,
        clientes: ClienteRepository,
        obras: ObraRepository,
        hasher: PasswordHasher,
        uow: UnitOfWork,
        admin_email: str,
        admin_password: str,
        operativo_email: str = "operativo@vrf.local",
        operativo_password: str = "change-me",
    ) -> None:
        self._grupos = grupos
        self._especialidades = especialidades
        self._empresas = empresas
        self._usuarios = usuarios
        self._rubros = rubros
        self._tipos = tipos
        self._clientes = clientes
        self._obras = obras
        self._hasher = hasher
        self._uow = uow
        self._admin_email = admin_email
        self._admin_password = admin_password
        self._operativo_email = operativo_email
        self._operativo_password = operativo_password

    def execute(self) -> None:
        grupo_id = self._grupos.ensure_seed_grupo("VRF", "Dueño VRF")
        self._ensure_especialidad(grupo_id, "Climatización generales", "climatizacion_generales")
        self._ensure_especialidad(grupo_id, "Instalación eléctrica", "instalacion_electrica")
        self._uow.commit()
        gen = self._especialidades.get_by_slug(grupo_id, "climatizacion_generales")
        elec = self._especialidades.get_by_slug(grupo_id, "instalacion_electrica")
        assert gen and elec
        cuit_vrf = Cuit(CUIT_VRF).value
        cuit_elec = Cuit(CUIT_ELEC).value
        vrf = self._empresas.get_by_cuit(cuit_vrf)
        if vrf is None:
            vrf = Empresa(
                id=uuid4(),
                grupo_id=grupo_id,
                razon_social="VRF S.A.",
                cuit=cuit_vrf,
                especialidad_id=gen.id,
                activa=True,
            )
            self._empresas.add(vrf)
        self._ensure_rubros(vrf.id, RUBROS_VRF)
        self._ensure_tipos(vrf.id)
        electrica = self._empresas.get_by_cuit(cuit_elec)
        if electrica is None:
            electrica = Empresa(
                id=uuid4(),
                grupo_id=grupo_id,
                razon_social="Eléctrica demo",
                cuit=cuit_elec,
                especialidad_id=elec.id,
                activa=True,
            )
            self._empresas.add(electrica)
        self._ensure_rubros(electrica.id, RUBROS_ELEC)
        self._ensure_tipos(electrica.id)
        self._ensure_demo_obra(grupo_id, vrf.id, electrica.id)
        self._ensure_usuario(
            grupo_id,
            self._admin_email,
            self._admin_password,
            Rol.ADMIN,
            [],
        )
        op_email = self._operativo_email.strip().lower()
        admin_email = self._admin_email.strip().lower()
        if op_email and op_email != admin_email:
            self._ensure_usuario(
                grupo_id,
                op_email,
                self._operativo_password,
                Rol.OPERATIVO,
                [vrf.id],
            )
        self._uow.commit()

    def _ensure_especialidad(self, grupo_id, nombre: str, slug: str) -> None:
        if self._especialidades.get_by_slug(grupo_id, slug) is None:
            self._especialidades.add(
                Especialidad(id=uuid4(), grupo_id=grupo_id, nombre=nombre, slug=slug)
            )

    def _ensure_rubros(self, empresa_id, nombres: list[str]) -> None:
        actuales = {r.nombre for r in self._rubros.list_by_empresa(empresa_id)}
        for nombre in nombres:
            if nombre in actuales:
                continue
            self._rubros.add(
                Rubro(
                    id=uuid4(),
                    empresa_id=empresa_id,
                    nombre=nombre,
                    clase=ClaseRubro.COMPRA_COSTO,
                    ambito=AmbitoRubro.AMBOS,
                )
            )

    def _ensure_tipos(self, empresa_id) -> None:
        actuales = {t.nombre for t in self._tipos.list_by_empresa(empresa_id)}
        for nombre, extra in TIPOS_PAGO:
            if nombre in actuales:
                continue
            self._tipos.add(
                TipoPago(id=uuid4(), empresa_id=empresa_id, nombre=nombre, schema_extra=extra)
            )

    def _ensure_usuario(
        self, grupo_id, email: str, password: str, rol: Rol, empresa_ids: list
    ) -> None:
        key = email.strip().lower()
        if self._usuarios.get_by_email(key) is not None:
            return
        self._usuarios.add(
            Usuario(
                id=uuid4(),
                grupo_id=grupo_id,
                email=key,
                password_hash=self._hasher.hash(password),
                rol=rol,
                empresa_ids=list(empresa_ids),
            )
        )

    def _ensure_demo_obra(self, grupo_id, vrf_id, elec_id) -> None:
        cliente = self._clientes.get_by_nombre(grupo_id, "Mostaza")
        if cliente is None:
            cliente = Cliente(id=uuid4(), grupo_id=grupo_id, nombre="Mostaza", cuit=None, activo=True)
            self._clientes.add(cliente)
        participantes = [vrf_id, elec_id]
        actual = next(
            (o for o in self._obras.list_by_grupo(grupo_id) if o.nombre == "Mostaza Rivadavia"),
            None,
        )
        if actual is None:
            self._obras.add(
                Obra(
                    id=uuid4(),
                    cliente_id=cliente.id,
                    nombre="Mostaza Rivadavia",
                    direccion="Av. Rivadavia 64",
                    tipo_trabajo=TipoTrabajo.INSTALACION,
                    estado=EstadoObra.ABIERTA,
                    empresa_ids=participantes,
                )
            )
            return
        faltan = [eid for eid in participantes if eid not in actual.empresa_ids]
        if faltan:
            actual.empresa_ids = list(dict.fromkeys([*actual.empresa_ids, *participantes]))
            self._obras.save(actual)
