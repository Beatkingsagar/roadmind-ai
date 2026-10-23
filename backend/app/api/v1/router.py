"""Main API v1 router combining all resource routers."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.admin import router as admin_router
from backend.app.api.v1.forecasting import router as forecasting_router
from backend.app.api.v1.incidents import router as incidents_router
from backend.app.api.v1.memory import router as memory_router
from backend.app.api.v1.network import router as network_router
from backend.app.api.v1.real_map import router as real_map_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.simulations import router as simulations_router

api_v1_router = APIRouter()

api_v1_router.include_router(network_router)
api_v1_router.include_router(real_map_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(forecasting_router)
api_v1_router.include_router(simulations_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(admin_router)
