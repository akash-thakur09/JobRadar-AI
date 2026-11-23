"""Candidate Evidence Vault for strictly truthful resume tailoring."""

import re
from typing import Any

from app.modules.candidate.models import CandidateProfile, CandidateSkill
from app.modules.jobs.models import Job
from app.modules.resumes.models import ResumeVersion

# Regular expression patterns for extracting numeric, percentage, multiplier, and currency claims
METRIC_PATTERNS = [
    # Percentages: 25%, 99.9%, -15%
    re.compile(r"-?\b\d+(?:\.\d+)?%"),
    # Currency amounts: $100k, $1.5M, $500,000, 50k USD
    re.compile(
        r"\$\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:k|m|b|billion|million|thousand))?\b", re.IGNORECASE
    ),
    re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:usd|eur|gbp)\b", re.IGNORECASE),
    # Multipliers: 2x, 10x, 3.5x
    re.compile(r"\b\d+(?:\.\d+)?x\b", re.IGNORECASE),
    # Number with quantifiable unit/scale (e.g. 500k users, 100+ requests, 15 engineers)
    re.compile(
        r"\b\d+(?:,\d{3})*(?:\.\d+)?\+?\s*(?:k|m|b)?\s*"
        r"(?:users|clients|customers|requests|queries|engineers|developers|"
        r"team members|direct reports|services|microservices|qps|rps|ms|percent)\b",
        re.IGNORECASE,
    ),
]


def extract_metrics_from_text(text: str) -> set[str]:
    """Extract normalized metric, quantitative, and percentage tokens from text."""
    metrics: set[str] = set()
    for pattern in METRIC_PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            # Clean and normalize metric string
            cleaned = re.sub(r"\s+", " ", m.strip().lower())
            metrics.add(cleaned)
    return metrics


class CandidateEvidenceVault:
    """Verifiable knowledge boundary compiled from trusted candidate profile and resume evidence."""

    def __init__(
        self,
        candidate_profile_id: str,
        full_name: str,
        headline: str | None,
        professional_summary: str | None,
        total_experience_months: int,
        skills: set[str],
        employers: set[str],
        titles: set[str],
        metrics: set[str],
        raw_experiences: list[dict[str, Any]],
        raw_projects: list[dict[str, Any]],
        raw_education: list[dict[str, Any]],
        job_title: str,
        job_company: str,
        job_description: str,
    ) -> None:
        self.candidate_profile_id = candidate_profile_id
        self.full_name = full_name
        self.headline = headline
        self.professional_summary = professional_summary
        self.total_experience_months = total_experience_months
        self.skills = {s.strip().lower() for s in skills if s.strip()}
        self.employers = {e.strip().lower() for e in employers if e.strip()}
        self.titles = {t.strip().lower() for t in titles if t.strip()}
        self.metrics = metrics
        self.raw_experiences = raw_experiences
        self.raw_projects = raw_projects
        self.raw_education = raw_education
        self.job_title = job_title
        self.job_company = job_company
        self.job_description = job_description

    @classmethod
    def from_entities(
        cls,
        candidate_profile: CandidateProfile,
        skills: list[CandidateSkill],
        resume_version: ResumeVersion,
        job: Job,
    ) -> "CandidateEvidenceVault":
        """Construct an evidence vault from database domain entities."""
        known_skills: set[str] = set()
        for s in skills:
            if s.skill_name:
                known_skills.add(s.skill_name.strip().lower())

        structured = resume_version.structured_content or {}

        # Add skills from structured parsed resume
        raw_skills = structured.get("skills", [])
        if isinstance(raw_skills, list):
            for r_skill in raw_skills:
                if isinstance(r_skill, str) and r_skill.strip():
                    known_skills.add(r_skill.strip().lower())

        known_employers: set[str] = set()
        known_titles: set[str] = set()
        known_metrics: set[str] = set()

        # Add profile headline & current role
        if candidate_profile.current_role:
            known_titles.add(candidate_profile.current_role.strip().lower())
        if candidate_profile.headline:
            known_titles.add(candidate_profile.headline.strip().lower())

        # Scan profile summary for metrics
        if candidate_profile.professional_summary:
            known_metrics.update(extract_metrics_from_text(candidate_profile.professional_summary))

        raw_experiences: list[dict[str, Any]] = []
        raw_projects: list[dict[str, Any]] = []
        raw_education: list[dict[str, Any]] = []

        # Parse experience section
        experience_data = structured.get("experience", [])
        if isinstance(experience_data, list):
            for exp in experience_data:
                if isinstance(exp, dict):
                    raw_experiences.append(exp)
                    comp = exp.get("company")
                    if comp and isinstance(comp, str):
                        known_employers.add(comp.strip().lower())
                    title = exp.get("title")
                    if title and isinstance(title, str):
                        known_titles.add(title.strip().lower())
                    bullets = exp.get("bullet_points") or exp.get("bullets", [])
                    if isinstance(bullets, list):
                        for b in bullets:
                            if isinstance(b, str):
                                known_metrics.update(extract_metrics_from_text(b))
                    elif isinstance(bullets, str):
                        known_metrics.update(extract_metrics_from_text(bullets))
                elif isinstance(exp, str):
                    # Fallback text bullet line
                    raw_experiences.append(
                        {"company": "Prior Experience", "title": "Role", "bullet_points": [exp]}
                    )
                    known_metrics.update(extract_metrics_from_text(exp))

        # Parse projects section
        projects_data = structured.get("projects", [])
        if isinstance(projects_data, list):
            for proj in projects_data:
                if isinstance(proj, dict):
                    raw_projects.append(proj)
                    desc = proj.get("description", "")
                    if isinstance(desc, str):
                        known_metrics.update(extract_metrics_from_text(desc))
                    techs = proj.get("technologies", [])
                    if isinstance(techs, list):
                        for t in techs:
                            if isinstance(t, str):
                                known_skills.add(t.strip().lower())
                elif isinstance(proj, str):
                    raw_projects.append(
                        {"name": "Project", "description": proj, "technologies": []}
                    )
                    known_metrics.update(extract_metrics_from_text(proj))

        # Parse education section
        education_data = structured.get("education", [])
        if isinstance(education_data, list):
            for edu in education_data:
                if isinstance(edu, dict):
                    raw_education.append(edu)
                elif isinstance(edu, str):
                    raw_education.append({"institution": edu, "degree": "Degree"})

        return cls(
            candidate_profile_id=str(candidate_profile.id),
            full_name=candidate_profile.full_name,
            headline=candidate_profile.headline,
            professional_summary=candidate_profile.professional_summary,
            total_experience_months=candidate_profile.total_experience_months,
            skills=known_skills,
            employers=known_employers,
            titles=known_titles,
            metrics=known_metrics,
            raw_experiences=raw_experiences,
            raw_projects=raw_projects,
            raw_education=raw_education,
            job_title=job.title,
            job_company=job.canonical_company_name,
            job_description=job.description_text,
        )

    def get_known_skills(self) -> set[str]:
        """Return lowercased verified candidate skills."""
        return set(self.skills)

    def get_known_employers(self) -> set[str]:
        """Return lowercased known employer names."""
        return set(self.employers)

    def get_known_titles(self) -> set[str]:
        """Return lowercased verified candidate job titles."""
        return set(self.titles)

    def get_known_metrics(self) -> set[str]:
        """Return normalized metrics extracted from verified source materials."""
        return set(self.metrics)

    def is_skill_supported(self, candidate_skill: str) -> bool:
        """Check if a skill is supported by evidence (case-insensitive substring/token match)."""
        clean = candidate_skill.strip().lower()
        if not clean:
            return False
        if clean in self.skills:
            return True
        for known in self.skills:
            if clean == known or clean in known or known in clean:
                return True
        return False

    def is_employer_supported(self, employer: str) -> bool:
        """Check if an employer name is grounded in source evidence."""
        clean = employer.strip().lower()
        if not clean:
            return False
        if not self.employers:
            # If no employer was explicitly extracted, permit generic or prior experience
            return True
        for known in self.employers:
            if clean in known or known in clean:
                return True
        return False

    def is_metric_supported(self, metric_str: str) -> bool:
        """Check if an extracted metric claim exists in known source metrics."""
        clean = re.sub(r"\s+", " ", metric_str.strip().lower())
        if clean in self.metrics:
            return True
        for known in self.metrics:
            if clean == known or clean in known or known in clean:
                return True
        return False

    def to_evidence_context(self) -> dict[str, Any]:
        """Format candidate facts into structured prompt context."""
        return {
            "candidate_profile": {
                "full_name": self.full_name,
                "headline": self.headline,
                "summary": self.professional_summary,
                "total_experience_years": round(self.total_experience_months / 12, 1),
            },
            "verified_skills": sorted(self.skills),
            "known_employers": sorted(self.employers),
            "known_titles": sorted(self.titles),
            "known_metrics": sorted(self.metrics),
            "employment_history": self.raw_experiences,
            "projects": self.raw_projects,
            "education": self.raw_education,
            "target_opportunity": {
                "title": self.job_title,
                "company": self.job_company,
                "description_excerpt": self.job_description[:2000],
            },
        }
