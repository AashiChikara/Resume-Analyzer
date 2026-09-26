import json
import os

from dotenv import load_dotenv
from google import genai

from schemas import ResumeAnalysis, JobDescriptionAnalysis
import hashlib

# Simple in-memory caches: same resume text or job description won't be
# sent to the LLM twice. Keyed by a hash of the text so long inputs don't
# bloat the cache key itself.
_resume_analysis_cache: dict[str, ResumeAnalysis] = {}
_jd_analysis_cache: dict[str, JobDescriptionAnalysis] = {}
_CACHE_MAX_SIZE = 100  # prevents unbounded memory growth


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _store_in_cache(cache: dict, key: str, value) -> None:
    if len(cache) >= _CACHE_MAX_SIZE:
        # Evict the oldest entry (dicts keep insertion order in Python 3.7+)
        oldest_key = next(iter(cache))
        cache.pop(oldest_key)
    cache[key] = value

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
    cache_key = _hash_text(resume_text)
    if cache_key in _resume_analysis_cache:
        return _resume_analysis_cache[cache_key]

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

    _store_in_cache(_resume_analysis_cache, cache_key, analysis)
    return analysis

from schemas import JobDescriptionAnalysis

JD_PROMPT = """
You are an assistant that extracts structured information from a job description.
Only extract what is actually written. Do not invent requirements.

Return ONLY a valid JSON object with exactly these keys, nothing else
(no markdown, no code fences, no explanation):

{{
  "required_skills": [],
  "technologies": [],
  "keywords": [],
  "responsibilities": [],
  "qualifications": []
}}

Rules:
- "required_skills": specific skills explicitly required (e.g. "Python", "communication").
- "technologies": tools, frameworks, platforms mentioned (e.g. "FastAPI", "AWS").
- "keywords": important terms a resume should ideally contain to match this job (e.g. "REST API", "CI/CD").
- "responsibilities": key duties described in the posting.
- "qualifications": education, years of experience, certifications required.

Job description:
\"\"\"
{job_description}
\"\"\"
"""


def analyze_job_description(job_description: str) -> JobDescriptionAnalysis:
    cache_key = _hash_text(job_description)
    if cache_key in _jd_analysis_cache:
        return _jd_analysis_cache[cache_key]

    prompt = JD_PROMPT.format(job_description=job_description)

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
        analysis = JobDescriptionAnalysis(**data)
    except Exception as e:
        raise ValueError(f"The LLM's response didn't match the expected structure: {e}")

    _store_in_cache(_jd_analysis_cache, cache_key, analysis)
    return analysis

from schemas import ImprovementResult

IMPROVE_PROMPT = """
You are helping someone improve a piece of their resume. Rewrite the text below
to sound clearer, more professional, and more action-oriented.

CRITICAL RULES:
- Do NOT invent numbers, percentages, metrics, or achievements that are not
  already present in the original text or in the additional context provided.
- Only reword and strengthen what is already true. Use stronger action verbs
  and clearer structure, but do not fabricate outcomes.
- If additional context is provided below, you may incorporate those specific
  facts, since the user confirmed they are true.

Section type: {section_type}

Original text:
\"\"\"
{original_text}
\"\"\"

Additional context (facts the user confirmed are true, may be empty):
\"\"\"
{additional_context}
\"\"\"

Return ONLY the improved text. No explanation, no quotes, no markdown.
"""


def improve_resume_text(section_type: str, original_text: str,
                         additional_context: str | None = None) -> ImprovementResult:
    """
    Ask Gemini to rewrite a piece of resume text without inventing facts.
    """
    prompt = IMPROVE_PROMPT.format(
        section_type=section_type,
        original_text=original_text,
        additional_context=additional_context or "None provided.",
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
    except Exception as e:
        raise ValueError(f"LLM API call failed: {e}")

    improved = (response.text or "").strip()
    if not improved:
        raise ValueError("The LLM returned an empty response.")

    return ImprovementResult(
        original_text=original_text,
        improved_text=improved,
    )