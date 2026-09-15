from uuid import uuid4

from vrf.domain.comprobante_reglas import validar_iva_si_hay_total
from vrf.domain.entities import Proveedor, Usuario
from vrf.domain.ports.ocr import OcrFactura, OcrResultado
from vrf.domain.ports.repositories import GrupoReader, ProveedorRepository, UnitOfWork


class PreviewOcr:
    def __init__(
        self,
        ocr: OcrFactura,
        proveedores: ProveedorRepository,
        grupos: GrupoReader,
        uow: UnitOfWork,
    ) -> None:
        self._ocr = ocr
        self._proveedores = proveedores
        self._grupos = grupos
        self._uow = uow

    def execute(self, _actor: Usuario, data: bytes, mime: str) -> dict:
        resultado = self._ocr.preview(data, mime)
        validar_iva_si_hay_total(
            resultado.neto_21,
            resultado.iva_21,
            resultado.neto_105,
            resultado.iva_105,
            resultado.neto_27,
            resultado.iva_27,
            resultado.no_gravado,
            resultado.percep_iva,
            resultado.percep_iibb,
            resultado.total,
        )
        proveedor, creado = self._vincular(resultado)
        return {
            "cuit_emisor": resultado.cuit_emisor,
            "razon_social": resultado.razon_social,
            "tipo_afip": resultado.tipo_afip.value if resultado.tipo_afip else None,
            "punto_venta": resultado.punto_venta,
            "numero": resultado.numero,
            "fecha": resultado.fecha.isoformat() if resultado.fecha else None,
            "neto_21": str(resultado.neto_21) if resultado.neto_21 is not None else None,
            "iva_21": str(resultado.iva_21) if resultado.iva_21 is not None else None,
            "neto_105": str(resultado.neto_105) if resultado.neto_105 is not None else None,
            "iva_105": str(resultado.iva_105) if resultado.iva_105 is not None else None,
            "neto_27": str(resultado.neto_27) if resultado.neto_27 is not None else None,
            "iva_27": str(resultado.iva_27) if resultado.iva_27 is not None else None,
            "no_gravado": str(resultado.no_gravado) if resultado.no_gravado is not None else None,
            "percep_iva": str(resultado.percep_iva) if resultado.percep_iva is not None else None,
            "percep_iibb": str(resultado.percep_iibb) if resultado.percep_iibb is not None else None,
            "total": str(resultado.total) if resultado.total is not None else None,
            "cae": resultado.cae,
            "incompleto": resultado.incompleto(),
            "proveedor_id": str(proveedor.id) if proveedor else None,
            "proveedor_creado": creado,
        }

    def _vincular(self, resultado: OcrResultado) -> tuple[Proveedor | None, bool]:
        if not resultado.cuit_emisor:
            return None, False
        existente = self._proveedores.get_by_cuit(resultado.cuit_emisor)
        if existente:
            return existente, False
        grupo_id, _ = self._grupos.get_unico()
        nombre = (resultado.razon_social or resultado.cuit_emisor).strip()
        item = Proveedor(
            id=uuid4(),
            grupo_id=grupo_id,
            razon_social=nombre,
            cuit=resultado.cuit_emisor,
        )
        self._proveedores.add(item)
        self._uow.commit()
        return item, True
