"""Layer 1: Deterministic Eligibility Engine (Hard Boolean Gates)."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    WorkplaceTypeEnum,
)
from app.modules.jobs.models import Job
from app.modules.matching.models import EligibilityStatusEnum

# Regex patterns for experience requirement extraction from job description and title
EXPERIENCE_PATTERN = re.compile(
    r"\b(\d+)\+?\s*(?:to\s*(\d+)\s*)?(?:years?|yrs?)(?:\s+of)?(?:\s+experience|\s+work\s+experience)?\b",
    re.IGNORECASE,
)

# Explicit work authorization and citizenship restrictions
VISA_RESTRICTION_PHRASES = [
    "no visa sponsorship",
    "no sponsorship",
    "unable to sponsor",
    "not able to sponsor",
    "must be a us citizen",
    "us citizenship required",
    "us citizen required",
    "security clearance required",
    "active secret clearance",
    "active ts/sci",
    "top secret clearance",
]

SPONSORSHIP_NEED_PHRASES = [
    "need sponsorship",
    "needs sponsorship",
    "requires sponsorship",
    "sponsorship required",
    "visa required",
    "h1b",
    "f1 opt",
]


@dataclass
class CheckResult:
    """Outcome of an individual deterministic eligibility check."""

    name: str
    passed: bool
    status: EligibilityStatusEnum
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EligibilityResult:
    """Aggregate result of Layer 1 Deterministic Eligibility evaluation."""

    is_eligible: bool
    status: EligibilityStatusEnum
    checks: dict[str, CheckResult] = field(default_factory=dict)
    failed_checks: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert eligibility outcome to structured dictionary for JSONB storage."""
        return {
            "is_eligible": self.is_eligible,
            "status": self.status.value,
            "failed_checks": self.failed_checks,
            "explanation": self.explanation,
            "checks": {
                name: {
                    "passed": check.passed,
                    "reason": check.reason,
                    "details": check.details,
                }
                for name, check in self.checks.items()
            },
        }


def extract_required_experience_months(job: Job) -> tuple[int, str]:
    """Deterministically extract minimum required experience in months from job text or seniority."""
    combined_text = f"{job.title}\n{job.description_text}"

    # 1. Search for explicit "X+ years of experience" statements
    matches = list(EXPERIENCE_PATTERN.finditer(combined_text))
    if matches:
        # Extract lowest mentioned year requirement in the context of requirements
        min_years = None
        for m in matches:
            years_val = int(m.group(1))
            # Filter realistic requirements (e.g. 1-20 years)
            if 1 <= years_val <= 20:
                if min_years is None or years_val < min_years:
                    min_years = years_val

        if min_years is not None:
            return (
                min_years * 12,
                f"Explicit {min_years} year(s) requirement found in job description.",
            )

    # 2. Seniority heuristic fallback from title
    title_lower = job.title.lower()
    if any(k in title_lower for k in ["principal", "staff", "director", "lead", "architect"]):
        return 96, "Seniority inferred as Staff/Lead (96 months minimum)."
    if any(k in title_lower for k in ["senior", "sr.", "sr ", "lead"]):
        return 60, "Seniority inferred as Senior (60 months minimum)."
    if any(k in title_lower for k in ["mid", "intermediate"]):
        return 36, "Seniority inferred as Mid (36 months minimum)."
    if any(k in title_lower for k in ["junior", "jr.", "jr ", "entry", "associate", "intern"]):
        return 12, "Seniority inferred as Junior/Entry (12 months minimum)."

    return 0, "No explicit experience requirement identified."


def check_job_freshness(
    job: Job,
    prefs: CandidatePreference,
    now: datetime,
) -> CheckResult:
    """Evaluate whether the job posting exceeds the candidate's max age threshold."""
    ref_time = job.posted_at or job.first_seen_at
    if ref_time is None:
        return CheckResult(
            name="job_freshness",
            passed=True,
            status=EligibilityStatusEnum.ELIGIBLE,
            reason="Posting timestamp missing; defaulted to eligible.",
            details={"max_job_age_days": prefs.max_job_age_days},
        )

    # Normalize timezone
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    age_days = (now - ref_time).total_seconds() / 86400.0
    passed = age_days <= prefs.max_job_age_days

    if passed:
        reason = f"Job age ({age_days:.1f} days) is within maximum allowed ({prefs.max_job_age_days} days)."
        status = EligibilityStatusEnum.ELIGIBLE
    else:
        reason = f"Job age ({age_days:.1f} days) exceeds maximum allowed age of {prefs.max_job_age_days} days."
        status = EligibilityStatusEnum.INELIGIBLE_EXPERIENCE

    return CheckResult(
        name="job_freshness",
        passed=passed,
        status=status,
        reason=reason,
        details={
            "job_age_days": round(age_days, 1),
            "max_job_age_days": prefs.max_job_age_days,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "first_seen_at": job.first_seen_at.isoformat() if job.first_seen_at else None,
        },
    )


def check_workplace_type(
    job: Job,
    prefs: CandidatePreference,
) -> CheckResult:
    """Evaluate whether the job's workplace arrangement is acceptable to the candidate."""
    if job.workplace_type == WorkplaceTypeEnum.UNKNOWN:
        return CheckResult(
            name="workplace_type",
            passed=True,
            status=EligibilityStatusEnum.ELIGIBLE,
            reason="Job workplace arrangement is unknown; preserved as eligible.",
            details={"job_workplace": job.workplace_type.value},
        )

    passed = job.workplace_type in prefs.preferred_workplace_types
    if passed:
        reason = f"Job workplace type '{job.workplace_type.value}' matches candidate preferences."
        status = EligibilityStatusEnum.ELIGIBLE
    else:
        pref_vals = [w.value for w in prefs.preferred_workplace_types]
        reason = (
            f"Job workplace type '{job.workplace_type.value}' not in preferred types ({pref_vals})."
        )
        status = EligibilityStatusEnum.INELIGIBLE_LOCATION

    return CheckResult(
        name="workplace_type",
        passed=passed,
        status=status,
        reason=reason,
        details={
            "job_workplace": job.workplace_type.value,
            "preferred_workplaces": [w.value for w in prefs.preferred_workplace_types],
        },
    )


def check_location(
    job: Job,
    profile: CandidateProfile,
    prefs: CandidatePreference,
) -> CheckResult:
    """Evaluate location compatibility for onsite or hybrid positions."""
    if job.workplace_type == WorkplaceTypeEnum.REMOTE:
        return CheckResult(
            name="location",
            passed=True,
            status=EligibilityStatusEnum.ELIGIBLE,
            reason="Remote position; location check satisfied.",
            details={"job_workplace": "REMOTE"},
        )

    if not job.normalized_location or not job.normalized_location.strip():
        return CheckResult(
            name="location",
            passed=True,
            status=EligibilityStatusEnum.ELIGIBLE,
            reason="Job location is unstated; preserved as eligible.",
            details={"job_location": None},
        )

    job_loc_lower = job.normalized_location.lower()
    allowed_locations: list[str] = [
        loc.lower().strip() for loc in prefs.preferred_locations if loc.strip()
    ]

    # Also add candidate profile city & country if present
    if profile.city and profile.city.strip():
        allowed_locations.append(profile.city.lower().strip())
    if profile.country and profile.country.strip():
        allowed_locations.append(profile.country.lower().strip())

    if not allowed_locations:
        return CheckResult(
            name="location",
            passed=True,
            status=EligibilityStatusEnum.ELIGIBLE,
            reason="No candidate location constraints configured.",
            details={"job_location": job.normalized_location},
        )

    # Check for substring or token overlap
    passed = False
    for allowed in allowed_locations:
        if allowed in job_loc_lower or job_loc_lower in allowed:
            passed = True
            break

    if passed:
        reason = f"Job location '{job.normalized_location}' matches candidate allowed locations."
        status = EligibilityStatusEnum.ELIGIBLE
    else:
        reason = f"Job location '{job.normalized_location}' does not match allowed locations."
        status = EligibilityStatusEnum.INELIGIBLE_LOCATION

    return CheckResult(
        name="location",
        passed=passed,
        status=status,
        reason=reason,
        details={
            "job_location": job.normalized_location,
            "allowed_locations": allowed_locations,
        },
    )


def check_experience_threshold(
    job: Job,
    profile: CandidateProfile,
    tolerance_buffer_months: int = 12,
) -> CheckResult:
    """Evaluate whether candidate experience satisfies the job's minimum requirement with grace buffer."""
    req_months, explanation = extract_required_experience_months(job)
    cand_months = profile.total_experience_months

    # Grace buffer formula from TD-005: candidate_months + tolerance >= req_months
    effective_cand_months = cand_months + tolerance_buffer_months
    passed = effective_cand_months >= req_months

    if passed:
        if cand_months >= req_months:
            reason = f"Candidate experience ({cand_months} mo) meets required ({req_months} mo)."
        else:
            reason = (
                f"Candidate experience ({cand_months} mo) qualifies within the "
                f"{tolerance_buffer_months}-month grace buffer (required: {req_months} mo)."
            )
        status = EligibilityStatusEnum.ELIGIBLE
    else:
        reason = (
            f"Candidate experience ({cand_months} mo) is below minimum requirement of {req_months} mo "
            f"(even with {tolerance_buffer_months}-month grace buffer)."
        )
        status = EligibilityStatusEnum.INELIGIBLE_EXPERIENCE

    return CheckResult(
        name="experience",
        passed=passed,
        status=status,
        reason=reason,
        details={
            "candidate_months": cand_months,
            "required_months": req_months,
            "tolerance_buffer_months": tolerance_buffer_months,
            "extraction_note": explanation,
        },
    )


def check_work_authorization(
    job: Job,
    profile: CandidateProfile,
) -> CheckResult:
    """Evaluate work authorization compatibility if restrictions are present in JD."""
    cand_auth = (profile.work_authorization or "").strip().lower()
    desc_lower = job.description_text.lower()

    # Check for sponsorship restriction in JD
    has_restriction = any(phrase in desc_lower for phrase in VISA_RESTRICTION_PHRASES)

    if not has_restriction:
        return CheckResult(
            name="work_authorization",
            passed=True,
            status=EligibilityStatusEnum.ELIGIBLE,
            reason="No visa or citizenship restrictions detected in job description.",
            details={"has_restriction": False},
        )

    # Check if candidate explicitly requires visa sponsorship
    needs_sponsorship = any(phrase in cand_auth for phrase in SPONSORSHIP_NEED_PHRASES)

    if needs_sponsorship and has_restriction:
        return CheckResult(
            name="work_authorization",
            passed=False,
            status=EligibilityStatusEnum.INELIGIBLE_WORK_AUTH,
            reason="Job specifies no visa sponsorship / US citizen requirement, but candidate requires sponsorship.",
            details={
                "has_restriction": True,
                "candidate_authorization": profile.work_authorization,
            },
        )

    return CheckResult(
        name="work_authorization",
        passed=True,
        status=EligibilityStatusEnum.ELIGIBLE,
        reason="Candidate authorization compatible with job requirements.",
        details={
            "has_restriction": has_restriction,
            "candidate_authorization": profile.work_authorization,
        },
    )


def check_mandatory_skills(
    _job: Job,
    mandatory_skills: set[str],
    job_skills: set[str],
) -> CheckResult:
    """Evaluate whether non-negotiable candidate skills are satisfied by the job."""
    if not mandatory_skills:
        return CheckResult(
            name="mandatory_skills",
            passed=True,
            status=EligibilityStatusEnum.ELIGIBLE,
            reason="No mandatory skills configured.",
            details={"mandatory_skills": []},
        )

    missing = mandatory_skills - job_skills
    passed = len(missing) == 0

    if passed:
        reason = f"All mandatory skills ({sorted(mandatory_skills)}) present in job posting."
        status = EligibilityStatusEnum.ELIGIBLE
    else:
        reason = f"Missing mandatory skill(s): {sorted(missing)}."
        status = EligibilityStatusEnum.INELIGIBLE_MANDATORY_SKILL

    return CheckResult(
        name="mandatory_skills",
        passed=passed,
        status=status,
        reason=reason,
        details={
            "mandatory_skills": sorted(mandatory_skills),
            "missing_skills": sorted(missing),
        },
    )


def evaluate_eligibility(
    job: Job,
    profile: CandidateProfile,
    prefs: CandidatePreference,
    job_skills: set[str] | None = None,
    mandatory_skills: set[str] | None = None,
    now: datetime | None = None,
) -> EligibilityResult:
    """Execute all Layer 1 Deterministic Eligibility gates in strict order.

    A failure in any hard gate halts qualification immediately.
    """
    current_time = now or datetime.now(UTC)
    skills = job_skills or set()
    required_mandatory = mandatory_skills or set()

    checks: dict[str, CheckResult] = {}
    failed_checks: list[str] = []
    first_failure_status: EligibilityStatusEnum = EligibilityStatusEnum.ELIGIBLE

    # Gate 1: Job Freshness
    freshness = check_job_freshness(job, prefs, current_time)
    checks["freshness"] = freshness
    if not freshness.passed:
        failed_checks.append("freshness")
        first_failure_status = freshness.status

    # Gate 2: Workplace Type
    workplace = check_workplace_type(job, prefs)
    checks["workplace"] = workplace
    if not workplace.passed:
        failed_checks.append("workplace")
        if first_failure_status == EligibilityStatusEnum.ELIGIBLE:
            first_failure_status = workplace.status

    # Gate 3: Location
    location = check_location(job, profile, prefs)
    checks["location"] = location
    if not location.passed:
        failed_checks.append("location")
        if first_failure_status == EligibilityStatusEnum.ELIGIBLE:
            first_failure_status = location.status

    # Gate 4: Experience Threshold (with 12-month grace buffer)
    experience = check_experience_threshold(job, profile)
    checks["experience"] = experience
    if not experience.passed:
        failed_checks.append("experience")
        if first_failure_status == EligibilityStatusEnum.ELIGIBLE:
            first_failure_status = experience.status

    # Gate 5: Work Authorization
    auth = check_work_authorization(job, profile)
    checks["work_authorization"] = auth
    if not auth.passed:
        failed_checks.append("work_authorization")
        if first_failure_status == EligibilityStatusEnum.ELIGIBLE:
            first_failure_status = auth.status

    # Gate 6: Mandatory Must-Have Skills
    if required_mandatory:
        mand = check_mandatory_skills(job, required_mandatory, skills)
        checks["mandatory_skills"] = mand
        if not mand.passed:
            failed_checks.append("mandatory_skills")
            if first_failure_status == EligibilityStatusEnum.ELIGIBLE:
                first_failure_status = mand.status

    is_eligible = len(failed_checks) == 0

    if is_eligible:
        explanation = "Passed all Layer 1 deterministic eligibility gates."
        final_status = EligibilityStatusEnum.ELIGIBLE
    else:
        primary_fail = checks[failed_checks[0]]
        explanation = f"Ineligible: {primary_fail.reason}"
        final_status = first_failure_status

    return EligibilityResult(
        is_eligible=is_eligible,
        status=final_status,
        checks=checks,
        failed_checks=failed_checks,
        explanation=explanation,
    )
