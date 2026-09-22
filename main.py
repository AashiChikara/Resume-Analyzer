from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from resume_parser import extract_text_from_pdf
from ai_service import analyze_resume
from schemas import ResumeAnalysis
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
MAX_FILE_SIZE_MB = 5

app = FastAPI(title="AI Resume Analyzer")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/upload")
def upload_page():
    return FileResponse(BASE_DIR / "templates" / "upload.html")


@app.get("/analysis")
def analysis_page():
    return FileResponse(BASE_DIR / "templates" / "analysis.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    file_bytes = await file.read()

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File is too large. Max size is {MAX_FILE_SIZE_MB} MB.",
        )

    if size_mb == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        resume_text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "Resume uploaded successfully",
        "resume_text": resume_text,
    }


class AnalyzeRequest(BaseModel):
    """What the client must send us to analyze a resume."""
    resume_text: str


@app.post("/analyze-resume", response_model=ResumeAnalysis)
def analyze_resume_endpoint(payload: AnalyzeRequest):
    if not payload.resume_text or not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is missing or empty.")

    try:
        result = analyze_resume(payload.resume_text)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return result