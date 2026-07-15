from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from api import auth_router, hh_accounts_router
from api.dictionaries import router as dictionaries_router
from api.filters import router as filters_router
from api.vacancies import router as vacancies_router
from core.exceptions import AppError
from settings import settings
from utils.configure_sentry import configure_sentry
from utils.database import close_database
from utils.seeding import seed_roles

configure_sentry()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await seed_roles()
    yield
    await close_database()


app = FastAPI(title=settings.app_title, debug=settings.debug, lifespan=lifespan)
app.include_router(auth_router, prefix="/api")
app.include_router(hh_accounts_router, prefix="/api")
app.include_router(dictionaries_router, prefix="/api")
app.include_router(filters_router, prefix="/api")
app.include_router(vacancies_router, prefix="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    status_code = 422 if request.url.path.startswith(("/api/dictionaries", "/api/filters", "/api/vacancies")) else 400
    return JSONResponse(status_code=status_code, content={"detail": exc.errors()})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, __: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "Пользователь с такими данными уже существует"},
    )
