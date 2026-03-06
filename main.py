from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, profile, education, treatments, chat, consent, ai
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="DentConsent Python Backend")

# Allow CORS for the Android App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/api/uploads", StaticFiles(directory="uploads"), name="api_uploads")

app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(auth.router, prefix="", tags=["Auth-PHP-Fallback"])
app.include_router(profile.router, prefix="/api", tags=["Profile"])
app.include_router(profile.router, prefix="", tags=["Profile-PHP-Fallback"])
app.include_router(education.router, prefix="/api", tags=["Education"])
app.include_router(education.router, prefix="", tags=["Education-PHP-Fallback"])
app.include_router(treatments.router, prefix="/api", tags=["Treatments"])
app.include_router(treatments.router, prefix="", tags=["Treatments-PHP-Fallback"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(chat.router, prefix="", tags=["Chat-PHP-Fallback"])
app.include_router(consent.router, prefix="/api", tags=["Consent"])
app.include_router(consent.router, prefix="", tags=["Consent-PHP-Fallback"])
app.include_router(ai.router, prefix="/api", tags=["AI"])
app.include_router(ai.router, prefix="", tags=["AI-PHP-Fallback"])

@app.get("/")
def read_root():
    return {"message": "DentConsent Python Backend is running."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
