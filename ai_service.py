import json
import os

from dotenv import load_dotenv
from google import genai

from schemas import ResumeAnalysis

load_dotenv()  # reads variables from .env into the environment

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing. Check your .env file.")

client = genai.Client(api_key=GEMINI_API_KEY)

ANALYSIS_PROMPT = """
You are a resume analysis assistant. Read the resume text below and extract
information ONLY if it is actually present in the text. Do not invent or
assume anything that isn't written in the resume.

Return ONLY a valid JSON object with exactly these keys, and nothing else
(no markdown, no explanation, no code fences):

{{
  "skills": [],
  "education": [],
  "projects": [],
  "certifications": [],
  "experience": [],
  "strengths": [],
  "weaknesses": [],
  "missing_sections": [],
  "suggestions": []
}}

Rules:
- "skills": technical and soft skills explicitly mentioned.
- "education": degrees, institutions, years, as written.
- "projects": short descriptions of projects mentioned.
- "certifications": certifications explicitly listed, empty list if none.
- "experience": job titles/companies/durations as written.
- "strengths": genuine strengths visible from the content (e.g. "hands-on project experience").
- "weaknesses": gaps visible from the content (e.g. "no quantified achievements").
- "missing_sections": standard resume sections that are absent (e.g. "certifications", "summary").
- "suggestions": concrete, actionable improvement suggestions.

Resume text:
\"\"\"
{resume_text}
\"\"\"
"""


def _extract_json(raw_text: str) -> str:
    """
    Gemini sometimes wraps JSON in ```json ... ``` code fences even when told
    not to. This strips those fences if present.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]  # take content between first pair of fences
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def analyze_resume(resume_text: str) -> ResumeAnalysis:
    """
    Send resume text to Gemini and return a validated ResumeAnalysis object.
    Raises ValueError with a clear message if anything goes wrong.
    """
    prompt = ANALYSIS_PROMPT.format(resume_text=resume_text)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
    except Exception as e:
        raise ValueError(f"LLM API call failed: {e}")

    raw_text = response.text
    if not raw_text:
        raise ValueError("The LLM returned an empty response.")

    cleaned = _extract_json(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError("The LLM did not return valid JSON.")

    try:
        analysis = ResumeAnalysis(**data)
    except Exception as e:
        raise ValueError(f"The LLM's response didn't match the expected structure: {e}")

    return analysis