from fastapi import APIRouter

from app.features.auth.routes import auth_router
from app.features.export.routes import export_csv_router, export_google_router
from app.features.form.routes import form_router
from app.features.llm.routes import llm_router
from app.features.response.routes import response_router

main_router = APIRouter(prefix="/api/v1")
main_router.include_router(auth_router)
main_router.include_router(export_google_router)
main_router.include_router(export_csv_router)
main_router.include_router(form_router)
main_router.include_router(llm_router)
main_router.include_router(response_router)
