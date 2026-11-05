"""Prompt templates and context builders for Layer 3 LLM Semantic Analysis."""

import json
from typing import Any

from app.modules.candidate.models import CandidateProfile, CandidateSkill
from app.modules.jobs.models import Job
from app.modules.resumes.models import MasterResume

SEMANTIC_ANALYSIS_SYSTEM_PROMPT = """You are an expert technical recruiter and talent intelligence evaluation system.
Your task is to conduct an objective, evidence-based Layer 3 Semantic Analysis comparing a Candidate's verified background against a Canonical Job Description.

CORE EVALUATION PRINCIPLES:
1. FACTUAL GROUNDING: Base your evaluation EXCLUSIVELY on the provided Candidate Evidence and Job Description. Never fabricate, hallucinate, or assume unstated credentials, technologies, or achievements.
2. HONEST GAPS: If the job description requires a technology or experience that the candidate lacks direct evidence for, explicitly identify it as a gap.
3. TRANSFERABLE SKILLS: Identify genuine transferable capabilities ONLY when the candidate demonstrates a foundational technology that directly maps to a missing job requirement (e.g., Docker Compose -> Kubernetes, PostgreSQL -> MySQL, React -> Vue). The candidate_skill MUST be one the candidate actually possesses.
4. SCORING SCALE:
   - 90.00 - 100.00: Exceptional contextual alignment; candidate has solved near-identical problems at comparable scope.
   - 75.00 - 89.99: Strong alignment; candidate meets core architectural and technical responsibilities with minor gaps.
   - 60.00 - 74.99: Moderate alignment; transferable skills present but noticeable domain or depth gaps.
   - Below 60.00: Weak alignment; substantial misalignment in responsibilities or missing foundational tech.

You must output a single, valid JSON object matching the requested schema. No surrounding markdown, no explanations outside JSON."""


def build_candidate_context(
    profile: CandidateProfile,
    skills: list[CandidateSkill],
    active_resume: MasterResume | None = None,
) -> dict[str, Any]:
    """Extract structured, evidence-backed candidate profile and resume content."""
    verified_skills = [
        {
            "skill": s.skill_name,
            "category": s.category,
            "experience_months": s.experience_months,
            "is_core": s.is_core,
        }
        for s in skills
    ]

    context: dict[str, Any] = {
        "full_name": profile.full_name,
        "headline": profile.headline or "",
        "professional_summary": profile.professional_summary or "",
        "current_role": profile.current_role or "",
        "total_experience_months": profile.total_experience_months,
        "total_experience_years": round(profile.total_experience_months / 12.0, 1),
        "location": f"{profile.city or ''}, {profile.country or ''}".strip(", "),
        "work_authorization": profile.work_authorization or "Unspecified",
        "verified_skills": verified_skills,
    }

    # Extract resume structured content if present
    if active_resume and active_resume.versions:
        latest_version = active_resume.versions[0]
        content = latest_version.structured_content or {}

        resume_details: dict[str, Any] = {}
        if "work_experience" in content:
            resume_details["work_experience"] = content["work_experience"]
        if "projects" in content:
            resume_details["projects"] = content["projects"]
        if "education" in content:
            resume_details["education"] = content["education"]

        if resume_details:
            context["active_resume_content"] = resume_details

    return context


def build_candidate_text_corpus(
    profile: CandidateProfile,
    skills: list[CandidateSkill],
    active_resume: MasterResume | None = None,
) -> str:
    """Build a comprehensive plaintext corpus of all verified candidate facts."""
    parts: list[str] = [
        profile.full_name,
        profile.headline or "",
        profile.professional_summary or "",
        profile.current_role or "",
        " ".join(s.skill_name for s in skills),
    ]

    if active_resume and active_resume.versions:
        latest_version = active_resume.versions[0]
        content = latest_version.structured_content or {}
        # Serialize entire JSON text for keyword searching
        parts.append(json.dumps(content))

    return " ".join(filter(None, parts))


def build_job_context(
    job: Job,
    deterministic_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract canonical job context for LLM prompt."""
    context: dict[str, Any] = {
        "title": job.title,
        "company_name": job.canonical_company_name,
        "location": job.normalized_location or "Unspecified",
        "workplace_type": job.workplace_type.value,
        "employment_type": job.employment_type.value,
        "description": job.description_text,
    }

    if deterministic_details:
        skills_breakdown = deterministic_details.get("deterministic_breakdown", {}).get(
            "skills", {}
        )
        context["deterministic_skill_analysis"] = {
            "matched_required": skills_breakdown.get("matched_required", []),
            "missing_required": skills_breakdown.get("missing_required", []),
            "matched_preferred": skills_breakdown.get("matched_preferred", []),
        }

    return context


def build_semantic_analysis_prompt(
    candidate_context: dict[str, Any],
    job_context: dict[str, Any],
) -> str:
    """Generate the user prompt for Layer 3 Semantic Analysis."""
    return f"""### CANONICAL JOB DETAILS:
Title: {job_context.get("title")}
Company: {job_context.get("company_name")}
Location: {job_context.get("location")} ({job_context.get("workplace_type")})
Employment Type: {job_context.get("employment_type")}

Job Description:
{job_context.get("description")}

Deterministic Skill Overlap:
- Matched Required Skills: {job_context.get("deterministic_skill_analysis", {}).get("matched_required", [])}
- Missing Required Skills: {job_context.get("deterministic_skill_analysis", {}).get("missing_required", [])}
- Matched Preferred Skills: {job_context.get("deterministic_skill_analysis", {}).get("matched_preferred", [])}

---

### CANDIDATE VERIFIED EVIDENCE:
Headline: {candidate_context.get("headline")}
Total Experience: {candidate_context.get("total_experience_years")} years ({candidate_context.get("total_experience_months")} months)
Summary: {candidate_context.get("professional_summary")}
Verified Skills: {json.dumps(candidate_context.get("verified_skills", []), indent=2)}

Active Resume Content:
{json.dumps(candidate_context.get("active_resume_content", {}), indent=2)}

---

### INSTRUCTIONS:
Evaluate the contextual alignment between this candidate and the role:
1. Assign a holistic semantic_score between 0.00 and 100.00.
2. Select a recommendation category: STRONG_MATCH, GOOD_MATCH, BORDERLINE, or NOT_RECOMMENDED.
3. List 1 to 5 matching_strengths with specific citations from the candidate's background.
4. List matching_gaps where the candidate lacks direct evidence for key responsibilities.
5. Identify transferable_skills where the candidate demonstrates a skill that substitutes for a missing requirement.
6. Provide a confidence rating (0.0 to 1.0) and a concise reasoning_summary.
"""
