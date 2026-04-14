from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.presentation.api.exception_handlers import register_exception_handlers
from app.presentation.api.lifespan import app_lifespan
from app.presentation.api.routers.auth import router as auth_router
from app.presentation.api.routers.enrollment import router as enrollment_router
from app.presentation.api.routers.teacher_slots import router as teacher_slots_router
from app.presentation.api.routers.tasks import router as tasks_router

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=app_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(tasks_router, prefix="/api/v1")
app.include_router(enrollment_router, prefix="/api/v1")
app.include_router(teacher_slots_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}