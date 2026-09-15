import pytest

from vrf.domain.exceptions import InvalidInput
from vrf.domain.vos import Cuit, cuit_valido


def test_cuit_vrf_valido() -> None:
    assert cuit_valido("33-71117492-9")
    assert Cuit("33-71117492-9").value == "33711174929"


def test_cuit_invalido() -> None:
    assert not cuit_valido("20123456789")
    with pytest.raises(InvalidInput):
        Cuit("20123456789")
