from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from resume_parser import extract_text_from_pdf

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


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    # 1. Validate file type by extension and content-type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # 2. Read the file into memory
    file_bytes = await file.read()

    # 3. Validate file size
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File is too large. Max size is {MAX_FILE_SIZE_MB} MB.",
        )

    if size_mb == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # 4. Extract text, turning parser errors into clean HTTP errors
    try:
        resume_text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "Resume uploaded successfully",
        "resume_text": resume_text,
    }