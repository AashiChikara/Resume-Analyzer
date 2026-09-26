from sentence_transformers import SentenceTransformer, util

from schemas import MatchResult, ResumeScore

# Loaded once when the app starts, not on every request — this is a fairly
# large model file, so loading it per-request would be very slow.
model = SentenceTransformer("all-MiniLM-L6-v2")


def calculate_semantic_similarity(resume_text: str, job_description: str) -> float:
    """
    Convert both texts into embeddings (numeric vectors that represent
    meaning) and measure how similar those vectors are.
    Returns a percentage from 0 to 100.
    """
    embeddings = model.encode([resume_text, job_description])
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()

    # cosine similarity ranges roughly -1 to 1; clamp and convert to 0-100
    similarity = max(0.0, min(1.0, similarity))
    return round(similarity * 100, 2)


def _normalize(items: list[str]) -> set[str]:
    """Lowercase and strip so 'Python' and 'python ' are treated as the same."""
    return {item.strip().lower() for item in items if item.strip()}


def compare_lists(resume_items: list[str], job_items: list[str]) -> tuple[list[str], list[str]]:
    """
    Compare two lists (skills or keywords) and return what matches
    and what's missing from the resume, using simple case-insensitive
    substring matching rather than exact equality, since resumes rarely
    phrase things identically to job postings.
    """
    resume_set = _normalize(resume_items)
    resume_text_blob = " ".join(resume_set)

    matching = []
    missing = []

    for job_item in job_items:
        job_item_clean = job_item.strip().lower()
        if not job_item_clean:
            continue

        found = any(
            job_item_clean in resume_word or resume_word in job_item_clean
            for resume_word in resume_set
        ) or job_item_clean in resume_text_blob

        if found:
            matching.append(job_item)
        else:
            missing.append(job_item)

    return matching, missing


def calculate_match(
    resume_text: str,
    job_description: str,
    resume_skills: list[str],
    required_skills: list[str],
    job_keywords: list[str],
) -> MatchResult:
    """
    Combine semantic similarity with explicit skill/keyword overlap
    into one explainable match result.
    """
    semantic_score = calculate_semantic_similarity(resume_text, job_description)

    matching_skills, missing_skills = compare_lists(resume_skills, required_skills)
    matching_keywords, missing_keywords = compare_lists([resume_text], job_keywords)

    # Skill coverage: what fraction of required skills the resume has
    if required_skills:
        skill_coverage = len(matching_skills) / len(required_skills) * 100
    else:
        skill_coverage = 100.0

    # Overall score: weighted average of semantic similarity and skill coverage.
    # Weights are simple and explainable, not a black box.
    overall_score = round((semantic_score * 0.5) + (skill_coverage * 0.5), 2)

    return MatchResult(
        match_score=overall_score,
        semantic_similarity=semantic_score,
        matching_skills=matching_skills,
        missing_skills=missing_skills,
        matching_keywords=matching_keywords,
        missing_keywords=missing_keywords,
    )
    from schemas import ResumeScore, MatchResult
from schemas import ResumeAnalysis

# The standard sections we expect a complete resume to have.
STANDARD_SECTIONS = ["skills", "education", "experience", "projects", "certifications"]


def calculate_section_completeness(missing_sections: list[str]) -> float:
    """
    Score based on how many standard sections are missing from the resume.
    100% means nothing standard is missing.
    """
    if not missing_sections:
        return 100.0

    # Only count it against completeness if it's actually one of our standard sections
    relevant_missing = [
        s for s in missing_sections
        if s.strip().lower() in STANDARD_SECTIONS
    ]

    total = len(STANDARD_SECTIONS)
    missing_count = min(len(relevant_missing), total)
    completeness = (total - missing_count) / total * 100
    return round(completeness, 2)


def _coverage_percent(matching: list[str], missing: list[str]) -> float:
    """What percentage of a required list the resume actually covers."""
    total = len(matching) + len(missing)
    if total == 0:
        return 100.0  # nothing was required, so nothing is missing
    return round(len(matching) / total * 100, 2)


def calculate_resume_score(
    match_result: MatchResult,
    resume_analysis: ResumeAnalysis,
) -> ResumeScore:
    """
    Combine four independent, explainable factors into one overall score.
    Each factor is weighted equally (25%) — a simple, easy-to-defend choice
    rather than a tuned/opaque weighting scheme.
    """
    skill_match = _coverage_percent(match_result.matching_skills, match_result.missing_skills)
    keyword_match = _coverage_percent(match_result.matching_keywords, match_result.missing_keywords)
    semantic_match = match_result.semantic_similarity
    section_completeness = calculate_section_completeness(resume_analysis.missing_sections)

    overall = round(
        (skill_match * 0.25)
        + (keyword_match * 0.25)
        + (semantic_match * 0.25)
        + (section_completeness * 0.25),
        2,
    )

    return ResumeScore(
        overall_score=overall,
        skill_match=skill_match,
        keyword_match=keyword_match,
        semantic_match=semantic_match,
        section_completeness=section_completeness,
    )