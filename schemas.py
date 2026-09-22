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