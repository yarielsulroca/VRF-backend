class DomainError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class NotFound(DomainError):
    def __init__(self, message: str = "No encontrado") -> None:
        super().__init__("not_found", message)


class Unauthorized(DomainError):
    def __init__(self, message: str = "No autenticado") -> None:
        super().__init__("unauthorized", message)


class Forbidden(DomainError):
    def __init__(self, message: str = "Sin permiso") -> None:
        super().__init__("forbidden", message)


class Conflict(DomainError):
    def __init__(self, message: str, extra: dict | None = None) -> None:
        super().__init__("conflict", message)
        self.extra = extra or {}


class InvalidInput(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__("invalid", message)
