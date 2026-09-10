"""
Management utility for AI Interview Copilot.

Supported Commands:
    python manage.py runserver     -> Starts the web server
    python manage.py runserver 8080-> Starts on custom port
    python manage.py test          -> Runs test suite
"""
import sys
import uvicorn
import pytest
from config.settings import settings


def main():
    args = sys.argv[1:]
    command = args[0] if args else "runserver"

    if command == "runserver":
        port = int(args[1]) if len(args) > 1 and args[1].isdigit() else settings.PORT
        print("=" * 65)
        print(f"  🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        print(f"  Mode: {'Local Open-Source' if settings.USE_OPEN_SOURCE else 'Google Gemini Cloud'}")
        print(f"  Local Web App: http://{settings.HOST}:{port}")
        print(f"  Swagger Docs:  http://{settings.HOST}:{port}/docs")
        print("=" * 65)
        uvicorn.run(
            "ai_apps.main:app",
            host=settings.HOST,
            port=port,
            reload=settings.DEBUG,
        )
    elif command == "test":
        pytest.main(["tests"])
    else:
        print(f"Unknown command: '{command}'.")
        print("Available commands:")
        print("  python manage.py runserver [port]")
        print("  python manage.py test")


if __name__ == "__main__":
    main()
