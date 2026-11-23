"""LLM prompt templates and builders for Truthful Resume Tailoring."""

import json

from app.modules.jobs.models import Job
from app.modules.tailoring.evidence import CandidateEvidenceVault

TAILORING_SYSTEM_PROMPT = """You are an expert ATS-optimized Resume Tailoring Engine.
Your sole mission is to improve the relevance, presentation, and alignment of a candidate's resume for a specific target job posting WITHOUT CHANGING ANY FACTUAL TRUTH.

STRICT FACTUAL INTEGRITY RULES:
1. NEVER hallucinate or invent new employers, companies, clients, or work history.
2. NEVER hallucinate or invent job titles or seniority levels beyond what is verified.
3. NEVER invent new technical skills, libraries, tools, or frameworks not listed in the candidate's verified skills or experience.
4. NEVER invent metrics, percentages, revenue figures, user counts, performance multipliers, or team sizes that do not appear in the candidate's source evidence.
5. If the candidate worked on a project without a quantifiable metric, write an impactful action-oriented bullet point emphasizing methodologies and outcomes WITHOUT inventing fake numbers.
6. Reorder and emphasize the candidate's verified skills to prioritize those most relevant to the target opportunity.
7. Tailor the headline and executive summary to directly address the target role using the candidate's real qualifications.

You must respond with valid JSON strictly conforming to the requested schema.
"""


def build_tailoring_prompt(vault: CandidateEvidenceVault, job: Job) -> tuple[str, str]:
    """Construct system prompt and context-grounded user prompt for resume tailoring.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    evidence_ctx = vault.to_evidence_context()

    user_prompt = f"""Please tailor the candidate's resume for the target job opportunity described below.

### TARGET JOB OPPORTUNITY
- **Role Title**: {job.title}
- **Company**: {job.canonical_company_name}
- **Location**: {job.normalized_location or "Not specified"}
- **Workplace Type**: {job.workplace_type.value if job.workplace_type else "Not specified"}
- **Job Description**:
{job.description_text[:3000]}

---

### CANDIDATE VERIFIED EVIDENCE VAULT
The following data represents the complete factual boundaries of what the candidate has actually done.
Do not invent anything outside this boundary.

{json.dumps(evidence_ctx, indent=2)}

---

### INSTRUCTIONS:
1. Formulate a targeted **headline** reflecting the candidate's background aligned with the '{job.title}' role.
2. Write a concise 3-4 sentence **professional_summary** highlighting candidate's verified strengths directly relevant to {job.canonical_company_name}.
3. Reorder the **skills** list: put the verified skills most relevant to the job at the top. Do NOT introduce unverified skills.
4. For each role in **experience**:
   - Keep the exact company name and role title from the evidence.
   - Rewrite the **bullet_points** to emphasize achievements relevant to the target role.
   - Preserve any real metrics from the evidence vault; DO NOT fabricate new percentages, dollar amounts, or numbers.
5. Include relevant **projects** and **education** from the evidence vault.
6. Include concise **tailoring_notes** summarizing your alignment rationale.

Respond ONLY with valid JSON matching the schema.
"""
    return TAILORING_SYSTEM_PROMPT, user_prompt
