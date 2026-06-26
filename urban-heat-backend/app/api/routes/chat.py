from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import get_settings
import httpx

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    context: str = ""

class ChatResponse(BaseModel):
    reply: str

@router.post("", response_model=ChatResponse)
def handle_chat(request: ChatRequest):
    settings = get_settings()
    api_key = settings.gemini_api_key.strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    prompt = (
        "You are HeatVision AI, an urban heat mitigation advisor. "
        "Answer the user's question about cooling recommendations or urban heat islands. "
        "Keep the answer concise, actionable, and friendly.\n\n"
    )
    if request.context:
        prompt += f"Context about the selected hotspot:\n{request.context}\n\n"
        
    prompt += f"User: {request.message}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 300,
        }
    }
    
    try:
        with httpx.Client(timeout=45) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to communicate with AI: {str(e)}")
