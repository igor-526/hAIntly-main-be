from .base import ClientError


class InvalidCredentials(ClientError):
    status_code = 401

    def __init__(self, message: str = "Неверный email или пароль") -> None:
        super().__init__(message)


class ForbiddenError(ClientError):
    status_code = 403

    def __init__(self, message: str = "Недостаточно прав доступа") -> None:
        super().__init__(message)
