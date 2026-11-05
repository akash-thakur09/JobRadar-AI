# AI Job Intelligence Platform — Hybrid Matching Engine Design

**Document ID:** TD-005  
**Status:** Approved Technical Design  
**Date:** 2026-11-04  
**Scope:** 3-Layer Matching Architecture, Deterministic Rules, Scoring Formulas, LLM Semantic Analysis, and Explainability  

---

# 1. Executive Summary & Design Principles

The JobRadar AI Matching Engine evaluates the relevance of discovered jobs against a candidate's profile and master resume. To avoid the hallucination and opacity risks inherent in purely LLM-based matching, while avoiding the rigid keyword blindness of legacy ATS systems, the platform utilizes a **Three-Layer Hybrid Matching Architecture**:

```text
┌────────────────────────────────────────────────────────┐
│           Layer 1: Deterministic Eligibility           │
│  Hard Gates: Location, Experience, Work Authorization  │
│  Outcome: PASS (Eligible) or FAIL (Drop from pipeline) │
└───────────────────────────┬────────────────────────────┘
                            │ Pass
                            ▼
┌────────────────────────────────────────────────────────┐
│           Layer 2: Deterministic Weighted Score        │
│  Normalized Skills (40%), Experience (20%),            │
│  Role Title (15%), Workplace/Location (15%), Other (10%)│
│  Outcome: 0.00 to 100.00 Mathematical Relevance Score  │
└───────────────────────────┬────────────────────────────┘
                            │ Preliminary Gate (Score >= 50)
                            ▼
┌────────────────────────────────────────────────────────┐
│           Layer 3: LLM Semantic Analysis               │
│  Contextual Alignment, Transferable Skills, Deep Gaps  │
│  Outcome: Validated Structured Semantic Evaluation     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Final Score & Explainability               │
│  Combined Weighted Score + Transparent Line-Item Breakdown │
└────────────────────────────────────────────────────────┘
```

### Core Invariants:
1. **No LLM Veto of Hard Constraints:** An LLM cannot mark an ineligible candidate as eligible, nor can it override hard constraints (e.g., location mismatch, mandatory visa restrictions).
2. **Explainability by Design:** Every score returned to the user must be decomposable into explicit mathematical line-item components.
3. **Graceful Degradation:** If the LLM provider fails, times out, or returns invalid schemas, the engine falls back to the deterministic score without interrupting the job pipeline.
4. **Candidate Evidence Traceability:** Matching evaluates candidate skills sourced exclusively from the candidate's verified profile and active resume.

---

# 2. Layer 1: Deterministic Eligibility Rules (Hard Constraints)

Layer 1 acts as a strict boolean filter. If any hard eligibility rule fails, the job is disqualified immediately, saving computational resources and preventing irrelevant resume tailoring.

## 2.1 Rule Specifications

| Constraint | Evaluation Logic | Failure Status |
| :--- | :--- | :--- |
| **Job Freshness** | `NOW() - job.posted_at <= candidate_preferences.max_job_age_days`. If `posted_at` is `NULL`, evaluate `NOW() - job.first_seen_at`. | `INELIGIBLE_EXPERIENCE` (stale job) |
| **Workplace Type** | Check if `job.workplace_type` is present in `candidate_preferences.preferred_workplace_types`. If job is `ONSITE` and candidate only accepts `REMOTE`, rule fails. | `INELIGIBLE_LOCATION` |
| **Location Match** | If job is `ONSITE` or `HYBRID`, evaluate geographic compatibility between `job.normalized_location` and candidate's allowed cities/countries. | `INELIGIBLE_LOCATION` |
| **Minimum Experience** | `candidate_profile.total_experience_months >= (job_analysis.minimum_experience_months - tolerance_buffer)`. (A 12-month grace buffer is applied so a candidate with 4.5 years is not rejected by a "5+ years" requirement). | `INELIGIBLE_EXPERIENCE` |
| **Work Authorization** | If the job posting explicitly specifies "No Visa Sponsorship" or "Must be a US Citizen", and the candidate's authorization does not match, rule fails. | `INELIGIBLE_WORK_AUTH` |
| **Mandatory Must-Have Skills**| If the candidate preference defines non-negotiable skills (e.g., candidate refuses non-Python jobs), job must contain the skill in `job_analysis.required_skills`. | `INELIGIBLE_MANDATORY_SKILL` |

If any check fails, `job_matches.eligibility_status` is updated with the respective failure code, and the processing pipeline halts for this job.

---

# 3. Layer 2: Deterministic Weighted Scoring

Layer 2 calculates an objective relevance score on a scale from `0.00` to `100.00`.

## 3.1 Scoring Formula

$$\text{Deterministic Score} = S_{\text{skills}} + S_{\text{experience}} + S_{\text{title}} + S_{\text{workplace}} + S_{\text{bonus}}$$

### Default Category Weights:

| Category | Maximum Points | Sub-Components |
| :--- | :--- | :--- |
| **Skill Coverage ($S_{\text{skills}}$)** | **40 pts** | Required Skills (30 pts) + Preferred Skills (10 pts) |
| **Experience Relevance ($S_{\text{experience}}$)** | **20 pts** | Seniority alignment & years in target domain |
| **Role Title Similarity ($S_{\text{title}}$)** | **15 pts** | Trigram string similarity & title taxonomy match |
| **Workplace / Location ($S_{\text{workplace}}$)** | **15 pts** | Exact city match, remote alignment, commute zone |
| **Domain / Industry Bonus ($S_{\text{bonus}}$)** | **10 pts** | Secondary keywords and domain familiarity |
| **Total Available** | **100 pts** | |

---

## 3.2 Skill Normalization & Alias Dictionary

Raw text in job descriptions and resumes uses varied synonyms for identical technologies. The platform runs all extracted skills through a **Skill Normalization Engine** before computing overlap.

### Normalization Pipeline:
1. **Case & Punctuation Stripping:** Convert to lowercase, remove periods and spaces (e.g., `"Node.js"` → `"nodejs"`, `"C++"` → `"cpp"`).
2. **Canonical Mapping via Taxonomy:**

```text
Alias Examples:
- ["postgres", "postgresql", "psql", "pgsql"]           ──> "postgresql"
- ["react", "reactjs", "react.js"]                     ──> "react"
- ["aws", "amazon web services", "amazon aws"]          ──> "aws"
- ["k8s", "kubernetes"]                                 ──> "kubernetes"
- ["golang", "go language", "go"]                       ──> "go"
- ["typescript", "ts"]                                  ──> "typescript"
- ["rest api", "restful api", "restful web services"]   ──> "rest_apis"
```

### Skill Score Formulation ($S_{\text{skills}}$):
Let:
- $R$ = set of normalized required skills extracted from JD.
- $P$ = set of normalized preferred skills extracted from JD.
- $C$ = set of candidate verified skills.

$$S_{\text{skills}} = \left( 30 \times \frac{|R \cap C|}{|R|} \right) + \left( 10 \times \frac{|P \cap C|}{|P|} \right)$$

*(If $|R| = 0$, the 40 points are distributed proportionally to preferred skills and title similarity).*

---

## 3.3 Experience & Seniority Alignment ($S_{\text{experience}}$)

Experience scoring evaluates both total years and seniority title alignment:
- Let $E_{\text{req}}$ = JD required experience in months.
- Let $E_{\text{cand}}$ = Candidate total experience in months.

$$S_{\text{exp\_ratio}} = \min\left(1.0, \frac{E_{\text{cand}}}{E_{\text{req}}}\right) \times 15\text{ pts}$$

**Seniority Alignment (5 pts):**
- Candidate seniority level mapped: `Junior` (0-2y), `Mid` (3-5y), `Senior` (5-8y), `Staff/Lead` (8y+).
- If candidate seniority level matches job seniority: **+5 pts**.
- If candidate is one tier above/below: **+3 pts**.
- If mismatch > 1 tier: **0 pts**.

---

## 3.4 Role Title Relevance ($S_{\text{title}}$)

Title similarity is calculated using a hybrid of **PostgreSQL Trigram Similarity (`similarity()`)** and token overlap against candidate target titles:

$$\text{Token Overlap} = \frac{|\text{Tokens}(\text{Candidate Title}) \cap \text{Tokens}(\text{Job Title})|}{|\text{Tokens}(\text{Job Title})|}$$

$$S_{\text{title}} = \left( 0.5 \times \text{TrigramSimilarity} + 0.5 \times \text{TokenOverlap} \right) \times 15\text{ pts}$$

---

# 4. Layer 3: LLM Semantic Analysis

While deterministic scoring handles measurable metrics, job descriptions often contain nuanced requirements that keyword matching misses (e.g., "orchestrated high-throughput event-driven microservices" vs "built distributed systems with Kafka").

## 4.1 Activation Threshold
To conserve LLM compute and latency, Layer 3 is executed **only if**:
1. Layer 1 (Eligibility) = `ELIGIBLE`.
2. Layer 2 (Deterministic Score) $\ge 50.00$ points.

Jobs with deterministic scores below 50.00 are marked `REJECTED` without calling the LLM.

## 4.2 LLM Analysis Scope & Structured Output Schema

The LLM is prompted with the parsed JD text and the candidate's structured profile/resume. It must output a strict JSON payload adhering to the following Pydantic schema:

```python
class SemanticEvaluationOutput(BaseModel):
    semantic_relevance_score: float = Field(
        ge=0.0, le=100.0,
        description="Holistic contextual alignment score from 0 to 100"
    )
    matching_strengths: list[str] = Field(
        min_length=1, max_length=5,
        description="Explicit candidate strengths aligning with key JD responsibilities"
    )
    matching_gaps: list[str] = Field(
        default_factory=list, max_length=5,
        description="Specific requirements or technologies where candidate lacks direct evidence"
    )
    transferable_skills: list[str] = Field(
        default_factory=list,
        description="Skills candidate possesses that substitute for missing JD technologies"
    )
    recommendation: Literal["STRONG_MATCH", "GOOD_MATCH", "BORDERLINE", "NOT_RECOMMENDED"]
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Model confidence based on JD clarity and candidate detail"
    )
    reasoning_summary: str = Field(
        max_length=300,
        description="Executive summary explaining the match recommendation"
    )
```

---

# 5. Final Score Composition & Explainability

## 5.1 Score Combination Formula

$$\text{Final Score} = \left( \text{Deterministic Score} \times 0.60 \right) + \left( \text{Semantic Score} \times 0.40 \right)$$

### Justification of Weights:
- **60% Deterministic:** Anchors the evaluation in factual, verifiable reality (hard skill counts, experience years, location compatibility).
- **40% Semantic:** Allows the LLM to reward contextual relevance, project scale, and transferable capabilities without letting hallucinated reasoning dominate the decision.

## 5.2 Graceful Degradation on LLM Failure
If the LLM provider experiences timeouts, rate limits, or validation errors after 1 retry:
1. The engine automatically degrades to **Deterministic Only Mode**.
2. $\text{Final Score} = \text{Deterministic Score}$.
3. `match_explanation_details` records `"llm_degraded": true`.
4. The pipeline continues uninterrupted.

## 5.3 Transparent Explainability Schema

The platform persists the exact audit trail of the match calculation inside `job_matches.match_explanation_details`:

```json
{
  "eligibility": {
    "status": "ELIGIBLE",
    "checks_passed": ["location", "workplace_type", "experience_threshold", "job_age"]
  },
  "deterministic_breakdown": {
    "total_points": 76.5,
    "skills": {
      "earned": 32.0,
      "max": 40.0,
      "matched_required": ["python", "fastapi", "postgresql", "docker"],
      "missing_required": ["kubernetes"],
      "matched_preferred": ["redis"]
    },
    "experience": {
      "earned": 18.0,
      "max": 20.0,
      "candidate_years": 5.2,
      "required_years": 5.0
    },
    "title_similarity": {
      "earned": 13.5,
      "max": 15.0,
      "job_title": "Senior Backend Software Engineer",
      "candidate_title": "Senior Python Backend Developer"
    },
    "workplace": {
      "earned": 13.0,
      "max": 15.0,
      "type": "REMOTE"
    }
  },
  "semantic_evaluation": {
    "score": 84.0,
    "recommendation": "STRONG_MATCH",
    "strengths": [
      "Extensive experience architecting async REST APIs matches backend scalability requirements.",
      "Demonstrated database optimization in PostgreSQL aligns with data layer responsibilities."
    ],
    "gaps": [
      "No direct production evidence managing Kubernetes clusters."
    ],
    "transferable_skills": [
      "Docker Compose experience indicates foundational container knowledge."
    ]
  },
  "final_score": 79.5
}
```

---

# 6. Edge Cases & Handling Strategies

```text
┌─────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Edge Case                       │ Resolution Strategy                                    │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ JD has zero required skills     │ Rely on preferred skills; reallocate weight to title   │
│ listed in text                  │ similarity and LLM semantic evaluation.                │
│ Candidate has zero matching     │ Layer 2 score drops below 50; job is marked REJECTED;  │
│ skills                          │ pipeline halts before calling LLM.                     │
│ Job title is ambiguous or       │ Rely on description content and skill overlap; reduce  │
│ unconventional (e.g. "Ninja")   │ title weight in favor of semantic analysis.            │
│ Candidate slightly under years  │ 12-month grace buffer prevents hard rejection; slight   │
│ of experience requirement       │ deduction applied in experience scoring formula.       │
│ Missing posting date from ATS   │ Use platform `first_seen_at` for freshness evaluation; │
│                                 │ never fabricate `posted_at`.                           │
└─────────────────────────────────┴────────────────────────────────────────────────────────┘
```

