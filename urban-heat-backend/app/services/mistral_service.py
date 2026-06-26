"""Mistral AI — generate urban cooling recommendation narratives."""

import logging

import httpx

logger = logging.getLogger(__name__)

MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-small-latest"


class MistralService:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        if not api_key:
            raise ValueError("Mistral API key is required")
        self.api_key = api_key
        self.model = model

    def generate_cooling_narrative(self, analysis_summary: str, actions: list[str]) -> str:
        action_list = ", ".join(actions)
        prompt = (
            "You are an urban heat mitigation advisor for city planners in India. "
            "Write 2-3 sentences of clear, actionable cooling advice. "
            "Use only the facts provided. Do not invent numbers or statistics.\n\n"
            f"Heat analysis: {analysis_summary}\n"
            f"Recommended interventions: {action_list}"
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 256,
        }
        with httpx.Client(timeout=45) as client:
            response = client.post(MISTRAL_CHAT_URL, headers=headers, json=payload)
            if response.status_code == 401:
                raise ValueError("Invalid Mistral API key")
            if response.status_code != 200:
                raise ValueError(f"Mistral API error {response.status_code}: {response.text[:300]}")
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip()
