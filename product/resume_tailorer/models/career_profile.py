from dataclasses import dataclass, asdict, field as dataclass_field
from typing import Optional


@dataclass
class EducationEntry:
    """Single education entry in the Career Truth Profile."""
    degree: str  # e.g., "BS", "MS", "PhD"
    field: str  # e.g., "Computer Science"
    institution: str  # e.g., "MIT"
    year: int  # graduation year
    gpa: Optional[str] = None  # e.g., "3.9"
    notes: list[str] = dataclass_field(default_factory=list)  # e.g. scholarships, honors, projects


@dataclass
class WorkExperience:
    """Single work experience entry in the Career Truth Profile."""
    employer: str
    title: str
    dates: str  # e.g., "2020-2022" or "Jan 2020 - Present"
    responsibilities: list[str]  # bullet points of what they did
    accomplishments: list[str]  # measurable outcomes/achievements
    location: Optional[str] = None
    employment_type: Optional[str] = None  # e.g., "Full-time", "Contract"


@dataclass
class CareerTruthProfile:
    """
    The single source of truth for a candidate's experience.
    All resume tailoring draws ONLY from this profile — never fabricates.
    """
    contact_info: dict  # {"name": str, "email": str, "phone": str, "location": str}
    education: list[EducationEntry]
    work_experience: list[WorkExperience]
    skills: list[str]  # e.g., ["Python", "Go", "Kubernetes"]
    tools: list[str]  # e.g., ["Docker", "PostgreSQL", "AWS"]
    certifications: list[str]  # e.g., ["AWS Solutions Architect"]
    accomplishments: list[str]  # career-level accomplishments not tied to a specific job
    summary: str = ""  # professional summary paragraph, if the original resume had one

    @property
    def name(self) -> str:
        return self.contact_info.get("name", "Unknown")

    @property
    def email(self) -> str:
        return self.contact_info.get("email", "")

    @property
    def phone(self) -> str:
        return self.contact_info.get("phone", "")

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage/transmission."""
        return {
            "contact_info": self.contact_info,
            "education": [asdict(e) for e in self.education],
            "work_experience": [asdict(w) for w in self.work_experience],
            "skills": self.skills,
            "tools": self.tools,
            "certifications": self.certifications,
            "accomplishments": self.accomplishments,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CareerTruthProfile":
        """Deserialize from dictionary."""
        return cls(
            contact_info=data["contact_info"],
            education=[EducationEntry(**e) for e in data.get("education", [])],
            work_experience=[WorkExperience(**w) for w in data.get("work_experience", [])],
            skills=data.get("skills", []),
            tools=data.get("tools", []),
            certifications=data.get("certifications", []),
            accomplishments=data.get("accomplishments", []),
            summary=data.get("summary", ""),
        )
