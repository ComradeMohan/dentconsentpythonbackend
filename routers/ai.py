import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List, Dict, Optional

router = APIRouter()

GROQ_API_KEY = "your_key_here"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Simple in-memory history (mimics PHP sessions per IP for now)
chat_histories: Dict[str, List[Dict[str, str]]] = {}

class ChatRequest(BaseModel):
    message: str
    role: Optional[str] = "patient"

@router.post("/ai_chat.php")
@router.post("/ai_chat")
async def ai_chat(req: ChatRequest, request: Request):
    client_ip = request.client.host
    
    system_prompt = (
        "You are DentConsent AI, a friendly dental care assistant embedded in a patient consent app. "
        "Your job: help patients understand dental procedures, post-op care, medication effects, and oral hygiene. "
        "RULES: "
        "1. Answer ONLY dental/health-related questions. "
        "2. Keep every answer to 2-3 short sentences maximum. "
        "3. Always recommend consulting the treating dentist for diagnosis or emergencies. "
        "4. Refuse unrelated questions with: 'I can only help with dental and oral health questions.' "
        "5. Never give definitive diagnoses — only guidance and reassurance."
    )
    
    if req.role == 'doctor':
        system_prompt += " The user is a dentist — you may use clinical terminology."

    # Initialize history for this "session" (IP-based for simplicity)
    if client_ip not in chat_histories:
        chat_histories[client_ip] = [{"role": "system", "content": system_prompt}]
    
    history = chat_histories[client_ip]
    history.append({"role": "user", "content": req.message})
    
    # Keep history manageable (system prompt + last 20 messages)
    if len(history) > 21:
        chat_histories[client_ip] = [history[0]] + history[-20:]
        history = chat_histories[client_ip]

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": history,
        "max_tokens": 200,
        "temperature": 0.4
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            reply = data['choices'][0]['message']['content'].strip()
            history.append({"role": "assistant", "content": reply})
            
            return {"reply": reply, "success": True}
        except Exception as e:
            # Revert history if API failed so user can retry
            if len(history) > 0 and history[-1]["role"] == "user":
                history.pop()
            return {"reply": "I'm having trouble connecting to my brain right now. Please try again in a moment.", "success": False, "error": str(e)}
