from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import get_settings
from app.services.mistral_service import MistralService

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    context: str = ""

class ChatResponse(BaseModel):
    reply: str

@router.post("", response_model=ChatResponse)
def handle_chat(request: ChatRequest):
    settings = get_settings()
    api_key = settings.mistral_api_key.strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="Mistral API key not configured")
    
    mistral_service = MistralService(api_key=api_key)
    
    import httpx
    prompt = (
        "You are HeatVision AI, an urban heat mitigation advisor. "
        "Answer the user's question about cooling recommendations or urban heat islands. "
        "Keep the answer concise, actionable, and friendly.\n\n"
    )
    if request.context:
        prompt += f"Context about the selected hotspot:\n{request.context}\n\n"
        
    prompt += f"User: {request.message}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": mistral_service.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 300,
    }
    
    try:
        with httpx.Client(timeout=45) as client:
            response = client.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()
            return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to communicate with AI: {str(e)}")
