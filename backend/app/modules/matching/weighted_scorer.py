"""Layer 2: Deterministic Weighted Scoring Engine (0.00 to 100.00)."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    WorkplaceTypeEnum,
)
from app.modules.jobs.models import Job
from app.modules.matching.eligibility import extract_required_experience_months

SENIORITY_TIERS: dict[str, int] = {
    "junior": 0,
    "mid": 1,
    "senior": 2,
    "staff": 3,
}


@dataclass
class ScoreBreakdown:
    """Detailed mathematical breakdown of Layer 2 scoring components."""

    skill_score: Decimal
    experience_score: Decimal
    title_score: Decimal
    preference_score: Decimal
    bonus_score: Decimal
    deterministic_score: Decimal
    final_score: Decimal
    details: dict[str, Any] = field(default_factory=dict)


def _round_2dp(val: float | Decimal) -> Decimal:
    """Round a float or Decimal to 2 decimal places using standard ROUND_HALF_UP."""
    d = Decimal(str(val)) if isinstance(val, float) else val
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _compute_trigram_similarity(str1: str, str2: str) -> float:
    """Compute character 3-gram Sørensen–Dice similarity between two strings."""
    s1 = str1.strip().lower()
    s2 = str2.strip().lower()

    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    # Generate character 3-grams
    t1 = {s1[i : i + 3] for i in range(len(s1) - 2)} if len(s1) >= 3 else {s1}
    t2 = {s2[i : i + 3] for i in range(len(s2) - 2)} if len(s2) >= 3 else {s2}

    intersection = len(t1 & t2)
    return (2.0 * intersection) / (len(t1) + len(t2))


def _compute_token_overlap(str1: str, str2: str) -> float:
    """Compute exact word-token overlap ratio."""
    # Split on non-alphanumeric characters to treat 'java' and 'javascript' as distinct tokens
    tokens1 = {t for t in re.split(r"[^a-zA-Z0-9]+", str1.lower()) if t}
    tokens2 = {t for t in re.split(r"[^a-zA-Z0-9]+", str2.lower()) if t}

    if not tokens1 or not tokens2:
        return 0.0

    common = tokens1 & tokens2
    return len(common) / max(len(tokens1), len(tokens2))


def _infer_seniority_tier(title: str, experience_months: int) -> str:
    """Map title and years of experience into a canonical seniority tier."""
    lower = title.lower()
    if any(k in lower for k in ["principal", "staff", "lead", "director", "architect"]):
        return "staff"
    if any(k in lower for k in ["senior", "sr.", "sr "]):
        return "senior"
    if any(k in lower for k in ["junior", "jr.", "jr ", "associate", "entry", "intern"]):
        return "junior"

    # Fallback to experience months
    if experience_months >= 96:
        return "staff"
    if experience_months >= 60:
        return "senior"
    if experience_months >= 24:
        return "mid"
    return "junior"


def score_skills(
    candidate_skills: set[str],
    job_skills: set[str],
    required_skills: set[str] | None = None,
    preferred_skills: set[str] | None = None,
) -> tuple[Decimal, dict[str, Any]]:
    """Score candidate skills against job requirements (Maximum: 40.00 points).

    Formula from TD-005:
    - If required (R) and preferred (P) distinguished:
      Score = (30 * |R ∩ C| / |R|) + (10 * |P ∩ C| / |P|)
    - If general skills (J):
      Score = 40 * |J ∩ C| / |J|
    """
    if required_skills and len(required_skills) > 0:
        r_matched = required_skills & candidate_skills
        p_matched = (preferred_skills or set()) & candidate_skills

        r_score = (30.0 * len(r_matched)) / len(required_skills)
        p_score = (
            (10.0 * len(p_matched)) / max(1, len(preferred_skills or set()))
            if preferred_skills
            else 0.0
        )
        earned = min(40.0, r_score + p_score)

        details = {
            "earned": round(earned, 2),
            "max": 40.0,
            "matched_required": sorted(r_matched),
            "missing_required": sorted(required_skills - candidate_skills),
            "matched_preferred": sorted(p_matched),
        }
        return _round_2dp(earned), details

    if not job_skills:
        # Neutral fallback when no skills are detected in job text
        return _round_2dp(20.0), {
            "earned": 20.0,
            "max": 40.0,
            "matched_skills": [],
            "missing_skills": [],
            "note": "No technical skills identified in job posting; awarded neutral baseline.",
        }

    matched = job_skills & candidate_skills
    missing = job_skills - candidate_skills
    earned = (40.0 * len(matched)) / len(job_skills)
    earned = max(0.0, min(40.0, earned))

    details = {
        "earned": round(earned, 2),
        "max": 40.0,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "job_skills_count": len(job_skills),
        "candidate_skills_count": len(candidate_skills),
    }
    return _round_2dp(earned), details


def score_experience(
    candidate_months: int,
    required_months: int,
    candidate_seniority: str,
    job_seniority: str,
) -> tuple[Decimal, dict[str, Any]]:
    """Score experience and seniority alignment (Maximum: 20.00 points).

    Formula from TD-005:
    - Ratio component (max 15 pts): min(1.0, cand_exp / req_exp) * 15
    - Seniority alignment (max 5 pts): exact = +5, diff 1 = +3, diff > 1 = 0
    """
    if required_months <= 0:
        ratio_pts = 15.0 if candidate_months > 0 else 10.0
    else:
        ratio_pts = min(1.0, float(candidate_months) / float(required_months)) * 15.0

    cand_tier = SENIORITY_TIERS.get(candidate_seniority.lower(), 1)
    job_tier = SENIORITY_TIERS.get(job_seniority.lower(), 1)
    diff = abs(cand_tier - job_tier)

    if diff == 0:
        seniority_pts = 5.0
    elif diff == 1:
        seniority_pts = 3.0
    else:
        seniority_pts = 0.0

    earned = min(20.0, ratio_pts + seniority_pts)
    details = {
        "earned": round(earned, 2),
        "max": 20.0,
        "ratio_score": round(ratio_pts, 2),
        "seniority_score": round(seniority_pts, 2),
        "candidate_months": candidate_months,
        "required_months": required_months,
        "candidate_seniority": candidate_seniority,
        "job_seniority": job_seniority,
    }
    return _round_2dp(earned), details


def score_title(
    candidate_headline: str,
    preferred_titles: list[str],
    job_title: str,
) -> tuple[Decimal, dict[str, Any]]:
    """Score position title similarity and relevance (Maximum: 15.00 points).

    Formula from TD-005:
    Score = (0.5 * TrigramSimilarity + 0.5 * TokenOverlap) * 15
    """
    candidates_to_compare = [candidate_headline] + [t for t in preferred_titles if t.strip()]
    best_score = 0.0
    best_details: dict[str, Any] = {}

    for cand_t in candidates_to_compare:
        if not cand_t or not cand_t.strip():
            continue

        trigram_sim = _compute_trigram_similarity(cand_t, job_title)
        token_overlap = _compute_token_overlap(cand_t, job_title)

        combined_sim = (0.5 * trigram_sim) + (0.5 * token_overlap)
        score_val = min(15.0, combined_sim * 15.0)

        if score_val >= best_score:
            best_score = score_val
            best_details = {
                "earned": round(score_val, 2),
                "max": 15.0,
                "trigram_similarity": round(trigram_sim, 3),
                "token_overlap": round(token_overlap, 3),
                "compared_candidate_title": cand_t,
                "job_title": job_title,
            }

    if not best_details:
        best_details = {"earned": 0.0, "max": 15.0, "reason": "No candidate titles available."}

    return _round_2dp(best_score), best_details


def score_workplace(
    job: Job,
    profile: CandidateProfile,
    prefs: CandidatePreference,
) -> tuple[Decimal, dict[str, Any]]:
    """Score workplace arrangement and location preference alignment (Maximum: 15.00 points)."""
    wp = job.workplace_type
    preferred_types = prefs.preferred_workplace_types

    # 1. Exact preferred workplace match
    if wp in preferred_types and wp != WorkplaceTypeEnum.UNKNOWN:
        earned = 15.0
        reason = f"Exact match with preferred workplace arrangement ('{wp.value}')."
    elif wp == WorkplaceTypeEnum.UNKNOWN:
        earned = 8.0
        reason = "Job workplace arrangement is unknown; awarded neutral score."
    elif wp == WorkplaceTypeEnum.REMOTE:
        earned = 12.0
        reason = "Remote opportunity satisfies general work flexibility."
    elif wp == WorkplaceTypeEnum.HYBRID:
        # Check if candidate location matches
        job_loc = (job.normalized_location or "").lower()
        cand_city = (profile.city or "").lower()
        if cand_city and cand_city in job_loc:
            earned = 12.0
            reason = "Hybrid opportunity situated in candidate's resident city."
        else:
            earned = 6.0
            reason = "Hybrid opportunity outside primary resident city."
    else:  # ONSITE
        job_loc = (job.normalized_location or "").lower()
        cand_city = (profile.city or "").lower()
        if cand_city and cand_city in job_loc:
            earned = 10.0
            reason = "Onsite opportunity in candidate's resident city."
        else:
            earned = 4.0
            reason = "Onsite opportunity outside primary resident city."

    return _round_2dp(earned), {
        "earned": round(earned, 2),
        "max": 15.0,
        "workplace_type": wp.value,
        "reason": reason,
    }


def score_bonus_factors(
    job: Job,
    prefs: CandidatePreference,
    now: datetime,
) -> tuple[Decimal, dict[str, Any]]:
    """Score additional bonus factors (Maximum: 10.00 points).

    - Employment Type Match: +4.0 pts
    - Target Title Exact Match: +3.0 pts
    - Freshness Bonus (<= 3 days old): +3.0 pts
    """
    earned = 0.0
    breakdown: dict[str, float] = {}

    # 1. Preferred Employment Type Match (+4.0)
    if job.employment_type in prefs.preferred_employment_types:
        earned += 4.0
        breakdown["employment_type_bonus"] = 4.0
    else:
        breakdown["employment_type_bonus"] = 0.0

    # 2. Target Title Direct Match (+3.0)
    title_lower = job.title.lower()
    title_matched = False
    for pref_t in prefs.preferred_titles:
        if pref_t.strip().lower() in title_lower:
            title_matched = True
            break

    if title_matched:
        earned += 3.0
        breakdown["target_title_bonus"] = 3.0
    else:
        breakdown["target_title_bonus"] = 0.0

    # 3. Freshness Bonus (+3.0 if <= 3 days old)
    ref_time = job.posted_at or job.first_seen_at
    if ref_time:
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        age_days = (now - ref_time).total_seconds() / 86400.0
        if age_days <= 3.0:
            earned += 3.0
            breakdown["freshness_bonus"] = 3.0
        else:
            breakdown["freshness_bonus"] = 0.0
    else:
        breakdown["freshness_bonus"] = 0.0

    earned = min(10.0, earned)
    details = {
        "earned": round(earned, 2),
        "max": 10.0,
        **breakdown,
    }
    return _round_2dp(earned), details


def calculate_deterministic_score(
    job: Job,
    profile: CandidateProfile,
    prefs: CandidatePreference,
    job_skills: set[str],
    now: datetime | None = None,
) -> ScoreBreakdown:
    """Calculate the complete Layer 2 Deterministic Weighted Score (0.00 to 100.00)."""
    current_time = now or datetime.now(UTC)

    # 1. Normalize candidate skills from profile
    candidate_skills = {
        s.skill_name.lower().replace("-", " ").strip() for s in profile.skills if s.skill_name
    }

    # 2. Skills Match (40 pts)
    s_skills, skills_details = score_skills(candidate_skills, job_skills)

    # 3. Experience Match (20 pts)
    req_months, _ = extract_required_experience_months(job)
    cand_seniority = _infer_seniority_tier(profile.headline or "", profile.total_experience_months)
    job_seniority = _infer_seniority_tier(job.title, req_months)
    s_exp, exp_details = score_experience(
        candidate_months=profile.total_experience_months,
        required_months=req_months,
        candidate_seniority=cand_seniority,
        job_seniority=job_seniority,
    )

    # 4. Role Title Relevance (15 pts)
    s_title, title_details = score_title(
        candidate_headline=profile.headline or profile.current_role or "",
        preferred_titles=prefs.preferred_titles,
        job_title=job.title,
    )

    # 5. Workplace / Location (15 pts)
    s_workplace, wp_details = score_workplace(job, profile, prefs)

    # 6. Bonus Factors (10 pts)
    s_bonus, bonus_details = score_bonus_factors(job, prefs, current_time)

    # Total score calculation clamped 0.00 to 100.00
    raw_total = s_skills + s_exp + s_title + s_workplace + s_bonus
    total_score = max(Decimal("0.00"), min(Decimal("100.00"), raw_total))
    rounded_total = _round_2dp(total_score)

    details = {
        "total_score": float(rounded_total),
        "skills": skills_details,
        "experience": exp_details,
        "title": title_details,
        "workplace": wp_details,
        "bonus": bonus_details,
    }

    return ScoreBreakdown(
        skill_score=s_skills,
        experience_score=s_exp,
        title_score=s_title,
        preference_score=s_workplace,
        bonus_score=s_bonus,
        deterministic_score=rounded_total,
        final_score=rounded_total,  # For Milestone 6, final_score = deterministic_score
        details=details,
    )
