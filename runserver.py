"""
AI Interview Copilot — Run Server Script
Usage:
    python runserver.py
"""
import sys
import uvicorn
from config.settings import settings

def main():
    print("=" * 65)
    print(f"  Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  Mode: {'Local Open-Source' if settings.USE_OPEN_SOURCE else 'Google Gemini Cloud'}")
    print(f"  Local Web App: http://{settings.HOST}:{settings.PORT}")
    print(f"  Swagger Docs:  http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 65)

    uvicorn.run(
        "ai_apps.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

if __name__ == "__main__":
    main()
