from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.manager import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_db_and_tables()
    yield
    # Shutdown
    manager.stop_current_model()

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.errors import http_exception_handler, validation_exception_handler, general_exception_handler

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Operation ID Generator
def simplify_operation_ids(app: FastAPI):
    for route in app.routes:
        if isinstance(route, APIRoute):
            # Use the function name as the operation ID
            # e.g., get_models -> get_models
            route.operation_id = route.name

# Custom OpenAPI Schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    # Simplify operation IDs before generating schema
    simplify_operation_ids(app)
    
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="Real-time Vietnamese Speech-to-Text Research Dashboard",
        routes=app.routes,
    )
    # Hardcode server URL for hey-api generator
    openapi_schema["servers"] = [{"url": "http://localhost:8000"}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/")
def root():
    return {"message": "Welcome to Real-time STT API"}

from app.api.endpoints import router
app.include_router(router)
