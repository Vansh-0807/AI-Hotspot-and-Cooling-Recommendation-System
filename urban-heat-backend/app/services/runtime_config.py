"""Runtime API key overrides set from the UI (session-scoped, not persisted to disk)."""

from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    openweather_api_key: str = ""
    google_maps_api_key: str = ""
    gemini_api_key: str = ""
    mistral_api_key: str = ""

    def update(
        self,
        openweather_api_key: str | None = None,
        google_maps_api_key: str | None = None,
        gemini_api_key: str | None = None,
        mistral_api_key: str | None = None,
    ) -> None:
        if openweather_api_key is not None:
            self.openweather_api_key = openweather_api_key.strip()
        if google_maps_api_key is not None:
            self.google_maps_api_key = google_maps_api_key.strip()
        if gemini_api_key is not None:
            self.gemini_api_key = gemini_api_key.strip()
        if mistral_api_key is not None:
            self.mistral_api_key = mistral_api_key.strip()

    def effective_openweather(self, fallback: str = "") -> str:
        return self.openweather_api_key or fallback

    def effective_google_maps(self, fallback: str = "") -> str:
        return self.google_maps_api_key or fallback

    def effective_gemini(self, fallback: str = "") -> str:
        return self.gemini_api_key or fallback

    def effective_mistral(self, fallback: str = "") -> str:
        return self.mistral_api_key or fallback

    def status(self, settings_fallback: dict) -> dict:
        ow = self.effective_openweather(settings_fallback.get("openweather", ""))
        gm = self.effective_google_maps(settings_fallback.get("google_maps", ""))
        gem = self.effective_gemini(settings_fallback.get("gemini", ""))
        mistral = self.effective_mistral(settings_fallback.get("mistral", ""))
        ai_provider = "mistral" if mistral else ("gemini" if gem else "template")
        return {
            "openweather_configured": bool(ow),
            "google_maps_configured": bool(gm),
            "gemini_configured": bool(gem),
            "mistral_configured": bool(mistral),
            "ai_provider": ai_provider,
            "ml_model": "Isolation Forest + K-Means",
        }


_runtime = RuntimeConfig()


def get_runtime_config() -> RuntimeConfig:
    return _runtime
