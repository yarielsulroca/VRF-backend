from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from vrf.domain.agregados import (
    entra_compensacion,
    entra_kpi,
    entra_libro_iva,
    en_periodo,
    es_comprobado,
    filtrar_visibles,
    neto_sin_iva,
    porcentaje,
    rango_mes,
    solo_impuestos,
    sumar_totales,
    visible_para,
)
from vrf.domain.comprobante_reglas import exigir_empresa_actor
from vrf.domain.entities import Comprobante, Obra, Usuario
from vrf.domain.enums import Clasificacion, EstadoObra, EstadoPago, Rol
from vrf.domain.exceptions import Forbidden, InvalidInput, NotFound
from vrf.domain.ports.repositories import (
    ClienteRepository,
    ComprobanteRepository,
    EmpresaRepository,
    ObraRepository,
    ProveedorRepository,
    RubroRepository,
    TipoPagoRepository,
)
from vrf.domain.vos import Cuit, dinero

_CERO = Decimal("0.00")


def _periodo(mes: str | None, desde: date | None, hasta: date | None) -> tuple[date, date]:
    if mes:
        return rango_mes(mes)
    if desde is None or hasta is None:
        raise InvalidInput("Indicá mes (YYYY-MM) o desde y hasta")
    if desde > hasta:
        raise InvalidInput("desde no puede ser posterior a hasta")
    return desde, hasta


def _fmt_cuit(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        return Cuit(raw).formateado()
    except InvalidInput:
        return raw


def _fmt_nro(n: int | None, ancho: int) -> str:
    return f"{n:0{ancho}d}" if n is not None else ""


@dataclass
class TotalClasificacion:
    clasificacion: str
    total: Decimal


@dataclass
class TotalEmpresa:
    empresa_id: UUID
    razon_social: str
    total: Decimal


@dataclass
class TopObra:
    obra_id: UUID
    nombre: str
    total: Decimal
    porcentaje: Decimal


@dataclass
class PendienteDash:
    comprobante_id: UUID
    numero: int | None
    proveedor: str | None
    fecha: date
    obra: str | None
    total: Decimal


@dataclass
class Dashboard:
    desde: date
    hasta: date
    total_comprobado: Decimal
    sin_iva: Decimal
    solo_impuestos: Decimal
    obras_abiertas: int
    por_clasificacion: list[TotalClasificacion]
    por_empresa: list[TotalEmpresa]
    top_obras: list[TopObra]
    pendientes: list[PendienteDash]
    total_pendientes: Decimal


@dataclass
class FilaCosto:
    comprobante_id: UUID
    empresa_id: UUID
    fecha: date
    proveedor: str | None
    clasificacion: str
    rubro_tipo: str | None
    total: Decimal
    estado_pago: str
    suma: bool


@dataclass
class PagoPorTipo:
    tipo_pago_id: UUID
    nombre: str
    total: Decimal


@dataclass
class CardEmpresa:
    empresa_id: UUID
    razon_social: str
    absorbido: Decimal
    filas: list[FilaCosto]
    pagos_por_tipo: list[PagoPorTipo]


@dataclass
class CostosObra:
    obra_id: UUID
    nombre: str
    cliente_id: UUID
    cliente_nombre: str
    tipo_trabajo: str
    costo_grupo: Decimal
    empresas: list[CardEmpresa]


@dataclass
class ResumenObraCosto:
    obra_id: UUID
    nombre: str
    tipo_trabajo: str
    costo_grupo: Decimal
    por_empresa: list[TotalEmpresa]


@dataclass
class CostosCliente:
    cliente_id: UUID | None
    cliente_nombre: str | None
    obras: list[ResumenObraCosto]


@dataclass
class LibroIva:
    empresa_id: UUID
    mes: str
    filas: list[dict[str, str]] = field(default_factory=list)


class ConsultarDashboard:
    def __init__(
        self,
        comps: ComprobanteRepository,
        empresas: EmpresaRepository,
        obras: ObraRepository,
        proveedores: ProveedorRepository,
        grupos,
    ) -> None:
        self._comps = comps
        self._empresas = empresas
        self._obras = obras
        self._proveedores = proveedores
        self._grupos = grupos

    def execute(
        self,
        actor: Usuario,
        mes: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        empresa_id: UUID | None = None,
    ) -> Dashboard:
        d, h = _periodo(mes, desde, hasta)
        if empresa_id:
            exigir_empresa_actor(actor, empresa_id)
        filas = filtrar_visibles(
            actor, self._comps.listar(empresa_id=empresa_id, desde=d, hasta=h)
        )
        kpis = [c for c in filas if entra_kpi(c, d, h)]
        total = sumar_totales(kpis)
        por_clase = []
        for clase in Clasificacion:
            por_clase.append(
                TotalClasificacion(
                    clasificacion=clase.value,
                    total=sumar_totales([c for c in kpis if c.clasificacion == clase]),
                )
            )
        por_emp: dict[UUID, Decimal] = defaultdict(lambda: _CERO)
        for c in kpis:
            por_emp[c.empresa_id] += c.total
        empresas_out = []
        for eid, tot in por_emp.items():
            emp = self._empresas.get(eid)
            empresas_out.append(
                TotalEmpresa(
                    empresa_id=eid,
                    razon_social=emp.razon_social if emp else str(eid),
                    total=dinero(tot),
                )
            )
        empresas_out.sort(key=lambda x: x.total, reverse=True)

        por_obra: dict[UUID, Decimal] = defaultdict(lambda: _CERO)
        for c in kpis:
            if c.obra_id is None:
                continue
            por_obra[c.obra_id] += c.total
        top = []
        for oid, tot in sorted(por_obra.items(), key=lambda x: x[1], reverse=True)[:5]:
            obra = self._obras.get(oid)
            top.append(
                TopObra(
                    obra_id=oid,
                    nombre=obra.nombre if obra else str(oid),
                    total=dinero(tot),
                    porcentaje=porcentaje(dinero(tot), total),
                )
            )

        pendientes_src = [
            c
            for c in filas
            if c.estado_pago == EstadoPago.PENDIENTE and en_periodo(c.fecha, d, h)
        ]
        pendientes = [self._pendiente(c) for c in pendientes_src]
        grupo_id, _ = self._grupos.get_unico()
        obras = self._obras.list_by_grupo(grupo_id)
        if actor.rol != Rol.ADMIN:
            permitidas = set(actor.empresa_ids)
            obras = [o for o in obras if permitidas.intersection(o.empresa_ids)]
        if empresa_id:
            obras = [o for o in obras if empresa_id in o.empresa_ids]
        abiertas = sum(1 for o in obras if o.estado == EstadoObra.ABIERTA)
        return Dashboard(
            desde=d,
            hasta=h,
            total_comprobado=total,
            sin_iva=dinero(sum((neto_sin_iva(c) for c in kpis), _CERO)),
            solo_impuestos=dinero(sum((solo_impuestos(c) for c in kpis), _CERO)),
            obras_abiertas=abiertas,
            por_clasificacion=por_clase,
            por_empresa=empresas_out,
            top_obras=top,
            pendientes=pendientes,
            total_pendientes=sumar_totales(pendientes_src),
        )

    def _pendiente(self, c: Comprobante) -> PendienteDash:
        prov = self._proveedores.get(c.proveedor_id) if c.proveedor_id else None
        obra = self._obras.get(c.obra_id) if c.obra_id else None
        return PendienteDash(
            comprobante_id=c.id,
            numero=c.numero,
            proveedor=prov.razon_social if prov else None,
            fecha=c.fecha,
            obra=obra.nombre if obra else None,
            total=c.total,
        )


class ConsultarCostosObra:
    def __init__(
        self,
        comps: ComprobanteRepository,
        obras: ObraRepository,
        clientes: ClienteRepository,
        empresas: EmpresaRepository,
        proveedores: ProveedorRepository,
        rubros: RubroRepository,
        tipos: TipoPagoRepository,
    ) -> None:
        self._comps = comps
        self._obras = obras
        self._clientes = clientes
        self._empresas = empresas
        self._proveedores = proveedores
        self._rubros = rubros
        self._tipos = tipos

    def execute(self, actor: Usuario, obra_id: UUID) -> CostosObra:
        obra = self._obras.get(obra_id)
        if obra is None:
            raise NotFound("Obra inexistente")
        if actor.rol != Rol.ADMIN and not set(actor.empresa_ids).intersection(obra.empresa_ids):
            raise Forbidden()
        cliente = self._clientes.get(obra.cliente_id)
        comps = self._comps.listar(obra_id=obra_id)
        cards = self._cards(actor, obra, comps)
        costo_grupo = dinero(sum((card.absorbido for card in cards), _CERO))
        return CostosObra(
            obra_id=obra.id,
            nombre=obra.nombre,
            cliente_id=obra.cliente_id,
            cliente_nombre=cliente.nombre if cliente else "",
            tipo_trabajo=obra.tipo_trabajo.value,
            costo_grupo=costo_grupo,
            empresas=cards,
        )

    def _cards(self, actor: Usuario, obra: Obra, comps: list[Comprobante]) -> list[CardEmpresa]:
        out = []
        for eid in obra.empresa_ids:
            if not visible_para(actor, eid):
                continue
            emp = self._empresas.get(eid)
            de_emp = [c for c in comps if c.empresa_id == eid and c.estado_pago != EstadoPago.ANULADO]
            absorbido = sumar_totales([c for c in de_emp if entra_compensacion(c, obra.id)])
            filas = [self._fila(c) for c in sorted(de_emp, key=lambda x: x.fecha)]
            pagos: dict[UUID, Decimal] = defaultdict(lambda: _CERO)
            nombres: dict[UUID, str] = {}
            for c in de_emp:
                if c.clasificacion != Clasificacion.PAGO or not es_comprobado(c) or not c.tipo_pago_id:
                    continue
                pagos[c.tipo_pago_id] += c.total
                if c.tipo_pago_id not in nombres:
                    tipo = self._tipos.get(c.tipo_pago_id)
                    nombres[c.tipo_pago_id] = tipo.nombre if tipo else str(c.tipo_pago_id)
            out.append(
                CardEmpresa(
                    empresa_id=eid,
                    razon_social=emp.razon_social if emp else str(eid),
                    absorbido=absorbido,
                    filas=filas,
                    pagos_por_tipo=[
                        PagoPorTipo(tipo_pago_id=tid, nombre=nombres[tid], total=dinero(tot))
                        for tid, tot in pagos.items()
                    ],
                )
            )
        return out

    def _fila(self, c: Comprobante) -> FilaCosto:
        prov = self._proveedores.get(c.proveedor_id) if c.proveedor_id else None
        rubro_tipo = None
        if c.rubro_id:
            rubro = self._rubros.get(c.rubro_id)
            rubro_tipo = rubro.nombre if rubro else None
        elif c.tipo_pago_id:
            tipo = self._tipos.get(c.tipo_pago_id)
            rubro_tipo = tipo.nombre if tipo else None
        return FilaCosto(
            comprobante_id=c.id,
            empresa_id=c.empresa_id,
            fecha=c.fecha,
            proveedor=prov.razon_social if prov else None,
            clasificacion=c.clasificacion.value,
            rubro_tipo=rubro_tipo,
            total=c.total,
            estado_pago=c.estado_pago.value,
            suma=es_comprobado(c),
        )


class ListarCostos:
    def __init__(
        self,
        comps: ComprobanteRepository,
        obras: ObraRepository,
        clientes: ClienteRepository,
        empresas: EmpresaRepository,
        grupos,
    ) -> None:
        self._comps = comps
        self._obras = obras
        self._clientes = clientes
        self._empresas = empresas
        self._grupos = grupos

    def execute(self, actor: Usuario, cliente_id: UUID | None = None) -> CostosCliente:
        if cliente_id:
            cliente = self._clientes.get(cliente_id)
            if cliente is None:
                raise NotFound("Cliente inexistente")
            obras = self._obras.list_by_cliente(cliente_id)
            nombre = cliente.nombre
        else:
            grupo_id, _ = self._grupos.get_unico()
            obras = self._obras.list_by_grupo(grupo_id)
            cliente = None
            nombre = None
        if actor.rol != Rol.ADMIN:
            permitidas = set(actor.empresa_ids)
            obras = [o for o in obras if permitidas.intersection(o.empresa_ids)]
        comps = filtrar_visibles(actor, self._comps.listar())
        resumenes = []
        for obra in obras:
            por_emp = []
            costo = _CERO
            for eid in obra.empresa_ids:
                if not visible_para(actor, eid):
                    continue
                emp = self._empresas.get(eid)
                abs_e = sumar_totales(
                    [c for c in comps if c.empresa_id == eid and entra_compensacion(c, obra.id)]
                )
                costo += abs_e
                por_emp.append(
                    TotalEmpresa(
                        empresa_id=eid,
                        razon_social=emp.razon_social if emp else str(eid),
                        total=abs_e,
                    )
                )
            resumenes.append(
                ResumenObraCosto(
                    obra_id=obra.id,
                    nombre=obra.nombre,
                    tipo_trabajo=obra.tipo_trabajo.value,
                    costo_grupo=dinero(costo),
                    por_empresa=por_emp,
                )
            )
        return CostosCliente(cliente_id=cliente_id, cliente_nombre=nombre, obras=resumenes)


COLUMNAS_LIBRO_IVA = [
    "Tipo AFIP",
    "Punto de venta",
    "Número",
    "Fecha",
    "CUIT emisor",
    "Proveedor",
    "Obra",
    "Clasificación",
    "Rubro/Tipo",
    "Neto 21%",
    "IVA 21%",
    "Neto 10,5%",
    "IVA 10,5%",
    "Neto 27%",
    "IVA 27%",
    "No gravado",
    "Percepción IVA",
    "Percepción IIBB",
    "Total",
    "Estado",
]


class ExportarLibroIva:
    def __init__(
        self,
        comps: ComprobanteRepository,
        empresas: EmpresaRepository,
        obras: ObraRepository,
        proveedores: ProveedorRepository,
        rubros: RubroRepository,
        tipos: TipoPagoRepository,
    ) -> None:
        self._comps = comps
        self._empresas = empresas
        self._obras = obras
        self._proveedores = proveedores
        self._rubros = rubros
        self._tipos = tipos

    def execute(self, actor: Usuario, empresa_id: UUID, mes: str) -> LibroIva:
        exigir_empresa_actor(actor, empresa_id)
        if self._empresas.get(empresa_id) is None:
            raise NotFound("Empresa inexistente")
        d, h = rango_mes(mes)
        filas_src = [
            c
            for c in self._comps.listar(empresa_id=empresa_id, desde=d, hasta=h)
            if entra_libro_iva(c) and en_periodo(c.fecha, d, h)
        ]
        filas_src.sort(key=lambda c: (c.fecha, c.punto_venta or 0, c.numero or 0))
        return LibroIva(
            empresa_id=empresa_id,
            mes=mes,
            filas=[self._fila(c) for c in filas_src],
        )

    def _fila(self, c: Comprobante) -> dict[str, str]:
        prov = self._proveedores.get(c.proveedor_id) if c.proveedor_id else None
        obra = self._obras.get(c.obra_id) if c.obra_id else None
        rubro_tipo = ""
        if c.rubro_id:
            rubro = self._rubros.get(c.rubro_id)
            rubro_tipo = rubro.nombre if rubro else ""
        elif c.tipo_pago_id:
            tipo = self._tipos.get(c.tipo_pago_id)
            rubro_tipo = tipo.nombre if tipo else ""
        return {
            "Tipo AFIP": c.tipo_afip.value,
            "Punto de venta": _fmt_nro(c.punto_venta, 4),
            "Número": _fmt_nro(c.numero, 8),
            "Fecha": c.fecha.isoformat(),
            "CUIT emisor": _fmt_cuit(c.cuit_emisor),
            "Proveedor": prov.razon_social if prov else "",
            "Obra": obra.nombre if obra else "",
            "Clasificación": c.clasificacion.value,
            "Rubro/Tipo": rubro_tipo,
            "Neto 21%": str(c.neto_21),
            "IVA 21%": str(c.iva_21),
            "Neto 10,5%": str(c.neto_105),
            "IVA 10,5%": str(c.iva_105),
            "Neto 27%": str(c.neto_27),
            "IVA 27%": str(c.iva_27),
            "No gravado": str(c.no_gravado),
            "Percepción IVA": str(c.percep_iva),
            "Percepción IIBB": str(c.percep_iibb),
            "Total": str(c.total),
            "Estado": c.estado_pago.value,
        }
