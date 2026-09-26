from pydantic import BaseModel, Field


class ResumeAnalysis(BaseModel):
    """
    Structure we expect back from the LLM after analyzing a resume.
    Pydantic validates that every field exists and has the right type.
    If the AI's response doesn't match this shape, Pydantic raises an error
    instead of silently accepting bad data.
    """
    skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

class JobDescriptionAnalysis(BaseModel):
    """Structure we expect back from the LLM after analyzing a job description."""
    required_skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    """Result of comparing a resume against a job description."""
    match_score: float
    semantic_similarity: float
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    matching_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)

class ResumeScore(BaseModel):
    """
    An explainable score: every factor is shown individually so the number
    isn't a mysterious black box.
    """
    overall_score: float
    skill_match: float
    keyword_match: float
    semantic_match: float
    section_completeness: float
    note: str = (
        "This is an estimated score for guidance only. "
        "It is not the score used by any specific company's ATS."
    )


class ImprovementRequest(BaseModel):
    section_type: str  # "summary", "project", "skills", or "experience"
    original_text: str
    additional_context: str | None = None  # e.g. real metrics the user wants included


class ImprovementResult(BaseModel):
    original_text: str
    improved_text: str
    note: str = "Review this suggestion — do not include any detail that isn't true for you."