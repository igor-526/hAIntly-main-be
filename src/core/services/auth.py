import secrets
from uuid import UUID

from core.entities import User
from core.exceptions import AlreadyExistsError, ClientError, InvalidCredentials
from core.protocols.repositories import RoleRepositoryProtocol, UserRepositoryProtocol
from core.protocols.security import SecurityProtocol
from core.schemas import AuthTokens, LoginData, RegisterData, RoleOut, UserOut
from core.seeds.roles import USER_ROLE_NAME


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepositoryProtocol,
        roles: RoleRepositoryProtocol,
        security: SecurityProtocol,
        service_key: str,
    ) -> None:
        self.users = users
        self.roles = roles
        self.security = security
        self.service_key = service_key

    async def register(self, *, data: RegisterData) -> UserOut:
        email = str(data.email).strip().lower()
        if not any(char.isalpha() for char in data.password) or not any(char.isdigit() for char in data.password):
            raise ClientError("Пароль должен содержать хотя бы одну букву и одну цифру")
        if await self.users.get_by_email(email=email) is not None:
            raise AlreadyExistsError("Email уже используется")
        user = await self.users.create(
            user=User(
                email=email,
                password=self.security.hash_password(data.password),
            )
        )
        role = await self.roles.get_by_name(name=USER_ROLE_NAME)
        if role is None:
            raise RuntimeError("Базовая роль user не создана")
        await self.users.assign_role(user_id=user.id, role_id=role.id)
        return await self._to_output(user=user)

    async def login(self, *, data: LoginData) -> AuthTokens:
        email = str(data.email).strip().lower()
        user = await self.users.get_by_email(email=email)
        if user is None or not self.security.verify_password(data.password, user.password):
            raise InvalidCredentials()
        return self._issue_tokens(user=user)

    async def refresh(self, *, token: str) -> AuthTokens:
        payload = self.security.decode_token(token)
        if payload.get("type") != "refresh":
            raise InvalidCredentials("Некорректный тип токена")
        user = await self._user_from_payload(payload=payload)
        return self._issue_tokens(user=user)

    async def current_user(self, *, token: str) -> UserOut:
        payload = self.security.decode_token(token)
        if payload.get("type") != "access":
            raise InvalidCredentials("Некорректный тип токена")
        return await self._to_output(user=await self._user_from_payload(payload=payload))

    async def current_service_user(self, *, service_key: str, user_id: str) -> UserOut:
        if not secrets.compare_digest(service_key.encode(), self.service_key.encode()):
            raise InvalidCredentials()
        try:
            parsed_user_id = UUID(user_id)
        except (TypeError, ValueError) as exc:
            raise InvalidCredentials() from exc
        user = await self.users.get_by_id(user_id=parsed_user_id)
        if user is None:
            raise InvalidCredentials()
        return await self._to_output(user=user)

    async def _user_from_payload(self, *, payload: dict[str, object]) -> User:
        try:
            user_id = UUID(str(payload["sub"]))
            session_version = int(str(payload["session_version"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidCredentials("Некорректное содержимое токена") from exc
        user = await self.users.get_by_id(user_id=user_id)
        if user is None or user.session_version != session_version:
            raise InvalidCredentials("Сессия недействительна")
        return user

    def _issue_tokens(self, *, user: User) -> AuthTokens:
        return AuthTokens(
            access_token=self.security.create_access_token(subject=str(user.id), session_version=user.session_version),
            refresh_token=self.security.create_refresh_token(
                subject=str(user.id), session_version=user.session_version
            ),
        )

    async def _to_output(self, *, user: User) -> UserOut:
        roles = await self.users.get_roles(user_id=user.id)
        return UserOut(
            id=user.id,
            email=user.email,
            roles=[RoleOut.model_validate(role) for role in roles],
        )
