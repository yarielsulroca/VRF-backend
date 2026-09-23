from typing import Protocol


class EscritorPlanilla(Protocol):
    def xlsx(self, encabezados: list[str], filas: list[list[str]]) -> bytes: ...
