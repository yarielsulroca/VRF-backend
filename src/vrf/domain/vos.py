from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from vrf.domain.enums import TipoAfip
from vrf.domain.exceptions import InvalidInput

_PESOS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
_CENTAVO = Decimal("0.01")


def _solo_digitos(valor: str) -> str:
    return "".join(c for c in valor if c.isdigit())


def cuit_valido(valor: str) -> bool:
    d = _solo_digitos(valor)
    if len(d) != 11:
        return False
    total = sum(int(d[i]) * _PESOS[i] for i in range(10))
    dv = 11 - (total % 11)
    if dv == 11:
        dv = 0
    elif dv == 10:
        dv = 9
    return dv == int(d[10])


@dataclass(frozen=True)
class Cuit:
    value: str

    def __post_init__(self) -> None:
        d = _solo_digitos(self.value)
        if not cuit_valido(d):
            raise InvalidInput("CUIT inválido")
        object.__setattr__(self, "value", d)

    def formateado(self) -> str:
        v = self.value
        return f"{v[:2]}-{v[2:10]}-{v[10]}"


def dinero(valor) -> Decimal:
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor)).quantize(_CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ClaveAfip:
    cuit_emisor: str
    tipo_afip: TipoAfip
    punto_venta: int
    numero: int

    @classmethod
    def try_build(
        cls,
        cuit_emisor: str | None,
        tipo_afip: TipoAfip,
        punto_venta: int | None,
        numero: int | None,
    ) -> "ClaveAfip | None":
        if tipo_afip not in (TipoAfip.A, TipoAfip.B, TipoAfip.C):
            return None
        if not cuit_emisor or punto_venta is None or numero is None:
            return None
        return cls(cuit_emisor, tipo_afip, punto_venta, numero)
