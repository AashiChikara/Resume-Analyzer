from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from resume_parser import extract_text_from_pdf
from ai_service import analyze_resume, analyze_job_description
from schemas import ResumeAnalysis, JobDescriptionAnalysis, MatchResult
from matching_service import calculate_match
from database import init_db
from models import save_resume, save_analysis, save_job_match, get_history
from ai_service import analyze_resume, analyze_job_description, improve_resume_text
from schemas import ResumeAnalysis, JobDescriptionAnalysis, MatchResult, ResumeScore, ImprovementRequest, ImprovementResult
from matching_service import calculate_match, calculate_resume_score

BASE_DIR = Path(__file__).resolve().parent
MAX_FILE_SIZE_MB = 5

app = FastAPI(title="AI Resume Analyzer")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def on_startup():
    """Create database tables (if missing) when the app starts."""
    init_db()


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/upload")
def upload_page():
    return FileResponse(BASE_DIR / "templates" / "upload.html")


@app.get("/analysis")
def analysis_page():
    return FileResponse(BASE_DIR / "templates" / "analysis.html")


@app.get("/job-match")
def job_match_page():
    return FileResponse(BASE_DIR / "templates" / "job-match.html")


@app.get("/history")
def history_page():
    return FileResponse(BASE_DIR / "templates" / "history.html")


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

    try:
        resume_id = save_resume(filename=file.filename, extracted_text=resume_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save resume to database: {e}")

    return {
        "message": "Resume uploaded successfully",
        "resume_id": resume_id,
        "resume_text": resume_text,
    }


class AnalyzeRequest(BaseModel):
    resume_text: str
    resume_id: int | None = None  # optional: link this analysis to a saved resume


@app.post("/analyze-resume", response_model=ResumeAnalysis)
def analyze_resume_endpoint(payload: AnalyzeRequest):
    if not payload.resume_text or not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is missing or empty.")

    try:
        result = analyze_resume(payload.resume_text)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if payload.resume_id is not None:
        try:
            save_analysis(
                resume_id=payload.resume_id,
                strengths=result.strengths,
                weaknesses=result.weaknesses,
                suggestions=result.suggestions,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis succeeded but saving to database failed: {e}",
            )

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
    resume_id: int | None = None  # optional: link this match to a saved resume


@app.post("/match-resume", response_model=MatchResult)
def match_resume_endpoint(payload: MatchRequest):
    if not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is missing.")
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is missing.")

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

    if payload.resume_id is not None:
        try:
            save_job_match(
                resume_id=payload.resume_id,
                job_description=payload.job_description,
                match_score=result.match_score,
                matching_skills=result.matching_skills,
                missing_skills=result.missing_skills,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Match succeeded but saving to database failed: {e}",
            )

    return result

class ResumeScoreRequest(BaseModel):
    resume_text: str
    job_description: str
    resume_id: int | None = None


@app.post("/resume-score", response_model=ResumeScore)
def resume_score_endpoint(payload: ResumeScoreRequest):
    if not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is missing.")
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is missing.")

    try:
        resume_analysis = analyze_resume(payload.resume_text)
        jd_analysis = analyze_job_description(payload.job_description)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    match_result = calculate_match(
        resume_text=payload.resume_text,
        job_description=payload.job_description,
        resume_skills=resume_analysis.skills,
        required_skills=jd_analysis.required_skills,
        job_keywords=jd_analysis.keywords,
    )

    score = calculate_resume_score(match_result, resume_analysis)

    if payload.resume_id is not None:
        try:
            save_analysis(
                resume_id=payload.resume_id,
                strengths=resume_analysis.strengths,
                weaknesses=resume_analysis.weaknesses,
                suggestions=resume_analysis.suggestions,
                score=score.overall_score,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Score calculated but saving to database failed: {e}",
            )

    return score


@app.post("/improve-resume", response_model=ImprovementResult)
def improve_resume_endpoint(payload: ImprovementRequest):
    if not payload.original_text.strip():
        raise HTTPException(status_code=400, detail="Original text is missing.")

    valid_types = {"summary", "project", "skills", "experience"}
    if payload.section_type.lower() not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"section_type must be one of: {', '.join(valid_types)}",
        )

    try:
        result = improve_resume_text(
            section_type=payload.section_type,
            original_text=payload.original_text,
            additional_context=payload.additional_context,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return result


@app.get("/history-data")
def history_data():
    try:
        return get_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load history: {e}")