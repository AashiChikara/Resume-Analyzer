from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Folder where main.py lives. Makes file paths work no matter where you run the app from.
BASE_DIR = Path(__file__).resolve().parent

# Create the FastAPI application
app = FastAPI(title="AI Resume Analyzer")

# Serve CSS/images from the /static folder at the URL /static/...
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def home():
    """Return the home page."""
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/health")
def health_check():
    """Simple endpoint to confirm the server is running."""
    return {"status": "ok"}