from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from resume_parser import extract_text_from_pdf
from ai_service import analyze_resume
from schemas import ResumeAnalysis
from pydantic import BaseModel

from ai_service import analyze_resume, analyze_job_description
from schemas import ResumeAnalysis, JobDescriptionAnalysis, MatchResult
from matching_service import calculate_match

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

@app.get("/job-match")
def job_match_page():
    return FileResponse(BASE_DIR / "templates" / "job-match.html")

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

class JobDescriptionRequest(BaseModel):
    job_description: str


@app.post("/analyze-job-description", response_model=JobDescriptionAnalysis)
def analyze_job_description_endpoint(payload: JobDescriptionRequest):
    if not payload.job_description or not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is missing or empty.")

    try:
        result = analyze_job_description(payload.job_description)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return result


class MatchRequest(BaseModel):
    resume_text: str
    job_description: str


@app.post("/match-resume", response_model=MatchResult)
def match_resume_endpoint(payload: MatchRequest):
    if not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is missing.")
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is missing.")

    # Run both LLM analyses first, so we have skills/keywords to compare
    try:
        resume_analysis = analyze_resume(payload.resume_text)
        jd_analysis = analyze_job_description(payload.job_description)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    result = calculate_match(
        resume_text=payload.resume_text,
        job_description=payload.job_description,
        resume_skills=resume_analysis.skills,
        required_skills=jd_analysis.required_skills,
        job_keywords=jd_analysis.keywords,
    )

    return result