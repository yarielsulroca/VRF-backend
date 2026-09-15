from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from vrf.domain.enums import TipoAfip


@dataclass
class OcrResultado:
    cuit_emisor: str | None = None
    razon_social: str | None = None
    tipo_afip: TipoAfip | None = None
    punto_venta: int | None = None
    numero: int | None = None
    fecha: date | None = None
    neto_21: Decimal | None = None
    iva_21: Decimal | None = None
    neto_105: Decimal | None = None
    iva_105: Decimal | None = None
    neto_27: Decimal | None = None
    iva_27: Decimal | None = None
    no_gravado: Decimal | None = None
    percep_iva: Decimal | None = None
    percep_iibb: Decimal | None = None
    total: Decimal | None = None
    cae: str | None = None

    def incompleto(self) -> bool:
        return any(
            v is None
            for v in (
                self.cuit_emisor,
                self.tipo_afip,
                self.punto_venta,
                self.numero,
                self.fecha,
                self.total,
            )
        )


class OcrFactura(Protocol):
    def preview(self, data: bytes, mime: str) -> OcrResultado: ...
