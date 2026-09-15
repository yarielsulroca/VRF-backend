from uuid import uuid4

from vrf.adapters.inbound.api.routers.libro_iva import COLUMNAS_LIBRO_IVA, armar_csv
from vrf.application.use_cases.consultas import COLUMNAS_LIBRO_IVA as COLUMNAS_UC
from vrf.application.use_cases.consultas import LibroIva


def test_headers_cubren_rf19() -> None:
    for esperado in [
        "Tipo AFIP",
        "Punto de venta",
        "Número",
        "IVA 21%",
        "IVA 10,5%",
        "IVA 27%",
        "Percepción IVA",
        "Percepción IIBB",
        "Obra",
        "Rubro/Tipo",
        "Estado",
    ]:
        assert esperado in COLUMNAS_LIBRO_IVA
    assert COLUMNAS_LIBRO_IVA == COLUMNAS_UC


def test_csv_vacio_solo_headers() -> None:
    raw = armar_csv(LibroIva(empresa_id=uuid4(), mes="2026-09", filas=[]))
    lineas = raw.lstrip("\ufeff").strip().splitlines()
    assert len(lineas) == 1
    assert "Tipo AFIP" in lineas[0]
    assert "Total" in lineas[0]
    assert "Estado" in lineas[0]



def test_headers_cubren_rf19() -> None:
    for esperado in [
        "Tipo AFIP",
        "Punto de venta",
        "Número",
        "IVA 21%",
        "IVA 10,5%",
        "IVA 27%",
        "Percepción IVA",
        "Percepción IIBB",
        "Obra",
        "Rubro/Tipo",
        "Estado",
    ]:
        assert esperado in COLUMNAS_LIBRO_IVA
    assert COLUMNAS_LIBRO_IVA == COLUMNAS_UC
