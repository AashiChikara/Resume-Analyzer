# AI Resume Analyzer

An AI-powered web application that analyzes resumes, compares them against job
descriptions, and provides an explainable match score along with improvement
suggestions.

## Features

- Upload a resume in PDF format and extract its text
- AI-powered resume analysis: skills, education, projects, certifications,
  experience, strengths, weaknesses, and missing sections
- AI-powered job description analysis: required skills, technologies,
  keywords, responsibilities, qualifications
- Resume-to-job matching using semantic similarity (Sentence Transformers)
  combined with explicit skill/keyword comparison
- An explainable resume score broken into four transparent factors, rather
  than a single opaque number
- AI-generated suggestions to improve resume wording, without inventing
  fake achievements or metrics
- History of past resume analyses and matches, stored in PostgreSQL

## Tech Stack

| Layer          | Technology                     |
|----------------|---------------------------------|
| Backend        | Python, FastAPI                |
| PDF parsing    | PyMuPDF                        |
| AI analysis    | Gemini API (`google-genai`)    |
| Similarity     | Sentence Transformers          |
| Database       | PostgreSQL (raw SQL, `psycopg2`) |
| Validation     | Pydantic                       |
| Frontend       | HTML, CSS, vanilla JavaScript  |
| Deployment     | Render (backend), Vercel (frontend) |

No ORM, no frontend framework, and no additional AI orchestration libraries
were used — every request/response and every database query is explicit and
easy to trace.

## Architecture
Browser (HTML/CSS/JS)
│
▼
FastAPI (main.py)
├── resume_parser.py → PyMuPDF text extraction
├── ai_service.py → Gemini API calls + Pydantic validation
├── matching_service.py→ Sentence Transformers + scoring logic
├── database.py → PostgreSQL connection + schema
└── models.py → SQL queries for save/fetch


Each layer has one responsibility: parsing, AI calls, scoring math, and data
storage are all in separate files so any one piece can be explained or
changed independently.

## API Endpoints

| Method | Endpoint                 | Description                                  |
|--------|---------------------------|-----------------------------------------------|
| GET    | `/`                        | Home page                                     |
| GET    | `/upload`                  | Upload page                                   |
| GET    | `/analysis`                | Analysis page                                 |
| GET    | `/job-match`               | Job match page                                |
| GET    | `/history`                 | History page                                  |
| GET    | `/history-data`            | JSON history data                             |
| GET    | `/health`                  | Health check                                  |
| POST   | `/upload-resume`           | Upload a PDF, extract and save text           |
| POST   | `/analyze-resume`          | AI analysis of resume text                    |
| POST   | `/analyze-job-description` | AI analysis of a job description              |
| POST   | `/match-resume`            | Compare resume vs job description             |
| POST   | `/resume-score`            | Explainable four-factor resume score          |
| POST   | `/improve-resume`          | AI-improved rewrite of a resume section       |

Full interactive documentation is available at `/docs` when running locally.

## Setup Instructions

### Prerequisites
- Python 3.10+
- PostgreSQL installed and running
- A free Gemini API key from https://aistudio.google.com/apikey

### Installation

```bash
git clone https://github.com/YOUR-USERNAME/resume-analyzer.git
cd resume-analyzer
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### Database

Create a PostgreSQL database named `resume_analyzer` (via pgAdmin or `psql`).
Tables are created automatically on application startup.

### Run locally

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000`.

## Deployment

### Backend → Render
1. Push the repository to GitHub.
2. Create a new Web Service on Render, connected to the repo.
3. Set the build command: `pip install -r requirements.txt`
4. Set the start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (`GEMINI_API_KEY`, `DATABASE_URL`) in Render's
   dashboard — never commit them to GitHub.

### Database → Render PostgreSQL
1. Create a Render PostgreSQL instance.
2. Copy its connection string into `DATABASE_URL` on the backend service.

### Frontend → Vercel
Since the HTML/CSS is currently served directly by FastAPI, a separate
Vercel deployment is only needed if the frontend is split out as static
files calling the Render backend via its public URL. If serving everything
from Render, this step can be skipped.

## Future Improvements

- Real user authentication (a login system) instead of a single guest user
- Automated tests with `pytest` and FastAPI's `TestClient`
- Pagination on the history page
- Support for `.docx` resumes in addition to PDF
- Caching repeated LLM calls to reduce API usage

## Disclaimer

The resume score and match score are estimates intended to help guide
improvements. They are not the actual score used by any specific company's
Applicant Tracking System (ATS).

