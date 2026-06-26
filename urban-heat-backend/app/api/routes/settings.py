from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import SettingsStatusResponse, SettingsUpdateRequest
from app.services.runtime_config import get_runtime_config

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsStatusResponse)
def get_settings_status():
    settings = get_settings()
    runtime = get_runtime_config()
    status = runtime.status(
        {
            "openweather": settings.openweather_api_key,
            "google_maps": settings.google_maps_api_key,
            "gemini": settings.gemini_api_key,
            "mistral": settings.mistral_api_key,
        }
    )
    return SettingsStatusResponse(
        **status,
        demo_city=settings.target_city,
    )


@router.post("", response_model=SettingsStatusResponse)
def update_settings(request: SettingsUpdateRequest):
    settings = get_settings()
    runtime = get_runtime_config()
    runtime.update(
        openweather_api_key=request.openweather_api_key,
        google_maps_api_key=request.google_maps_api_key,
        gemini_api_key=request.gemini_api_key,
        mistral_api_key=request.mistral_api_key,
    )
    status = runtime.status(
        {
            "openweather": settings.openweather_api_key,
            "google_maps": settings.google_maps_api_key,
            "gemini": settings.gemini_api_key,
            "mistral": settings.mistral_api_key,
        }
    )
    return SettingsStatusResponse(
        **status,
        demo_city=settings.target_city,
    )
