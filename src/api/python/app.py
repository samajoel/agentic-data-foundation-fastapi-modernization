"""
Thin compatibility shim — keeps `python app.py` and `uvicorn app:app` working unchanged.

All application logic lives in the app/ package (app/main.py).
"""

from app.main import app, build_app  # noqa: F401
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
