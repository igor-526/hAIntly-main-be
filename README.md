# HAIntly Main Backend (`main-be`)

Публичный backend и оркестрационный шлюз HAIntly на FastAPI.

> Статус: архитектурная заготовка. Код, endpoint и команды запуска ещё не определены.

## Ответственность

- регистрация и подтверждение email;
- авторизация, аутентификация и управление пользователями;
- публичный HTTP API для `main-fe`;
- оркестрация профильных сервисов;
- получение уведомлений и доставка в UI по SSE.

## Интеграции

- HTTP ↔ `main-fe`;
- SSE → `main-fe`;
- HTTP → `profile-service`, `vacancy-service`, `ai-service`, `notification-service`;
- NATS JetStream ← `notification-service`.

## Владение данными

Сервис владеет пользователями HAIntly, auth-данными и собственной PostgreSQL БД. HH-токены, резюме, вакансии, AI-настройки и история уведомлений принадлежат профильным сервисам.

## Ограничения

- Не обращаться напрямую к БД другого сервиса.
- Не переносить профильную бизнес-логику в gateway.
- Не раскрывать внутренние ошибки, пароли и service token.
- Не определять endpoint или event schema без OpenSpec change.

Будущая документация должна добавить setup/dev/test, миграции, env, OpenAPI, SSE lifecycle и межсервисную авторизацию.

Общие границы проекта: [SERVICES.md](../../SERVICES.md).
# Vacancy dictionaries

Авторизованный read-only proxy доступен под `/api/dictionaries`. Адрес внутреннего `vacancy-service` и timeout задаются обязательными `VACANCY_SERVICE_URL` и `VACANCY_SERVICE_TIMEOUT_SECONDS`; UUID текущего пользователя передаётся только в `X-User-Id`.
