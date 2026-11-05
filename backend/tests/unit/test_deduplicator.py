"""Unit tests for deterministic slug formulation, URL sanitization, and deduplication."""

from app.modules.candidate.models import WorkplaceTypeEnum
from app.modules.jobs.deduplicator import (
    clean_html_description,
    compute_canonical_slug,
    compute_dedup_fingerprint,
    normalize_slug,
    sanitize_application_url,
)


def test_normalize_slug_removes_corporate_suffixes() -> None:
    assert normalize_slug("Stripe, Inc.") == "stripe"
    assert normalize_slug("Acme Corp.") == "acme"
    assert normalize_slug("Google LLC") == "google"
    assert normalize_slug("DeepMind Technologies") == "deepmind"
    assert normalize_slug("Example Ltd.") == "example"
    assert normalize_slug("Vercel Holdings") == "vercel"


def test_normalize_slug_expands_abbreviations() -> None:
    assert normalize_slug("Sr. Software Engineer") == "senior-software-engineer"
    assert normalize_slug("Jr. Developer") == "junior-developer"
    assert normalize_slug("Lead SWE") == "lead-software-engineer"
    assert normalize_slug("SW Eng - Backend") == "software-engineer-backend"
    assert (
        normalize_slug("Staff AI/ML Engineer")
        == "staff-artificial-intelligence-machine-learning-engineer"
    )
    assert normalize_slug("Lead QA Tester") == "lead-quality-assurance-tester"


def test_normalize_slug_whitespace_and_punctuation() -> None:
    assert (
        normalize_slug("  Senior   Backend    Engineer (Payments)  ")
        == "senior-backend-engineer-payments"
    )
    assert normalize_slug("---Hello---World---") == "hello-world"
    assert normalize_slug("") == ""
    assert normalize_slug("    ") == ""


def test_sanitize_application_url_strips_tracking_params() -> None:
    raw = (
        "http://jobs.lever.co/stripe/abc-123/?"
        "utm_source=linkedin&utm_medium=job_board&utm_campaign=hiring"
        "&gh_jid=12345&ref=indeed&source=newsletter&fbclid=xyz&token=secret"
        "&team=engineering&department=platform"
    )
    sanitized = sanitize_application_url(raw)
    assert sanitized.startswith("https://jobs.lever.co/stripe/abc-123")
    assert "utm_source" not in sanitized
    assert "gh_jid" not in sanitized
    assert "fbclid" not in sanitized
    assert "token" not in sanitized
    # Preserves non-tracking query params alphabetically sorted
    assert "department=platform&team=engineering" in sanitized


def test_sanitize_application_url_normalizes_case_and_trailing_slashes() -> None:
    url = "HTTP://JOBS.GREENHOUSE.IO/Stripe/Jobs/456789/INDEX.HTML"
    sanitized = sanitize_application_url(url)
    assert sanitized == "https://jobs.greenhouse.io/stripe/jobs/456789"

    url_with_slash = "https://boards.greenhouse.io/airbnb/jobs/12345/"
    assert (
        sanitize_application_url(url_with_slash) == "https://boards.greenhouse.io/airbnb/jobs/12345"
    )


def test_clean_html_description() -> None:
    raw_html = (
        "<h3>About the Role</h3>"
        "<p>We are looking for a <b>Senior Engineer</b> to join our payments team.</p>"
        "<p>Responsibilities include:</p>"
        "<ul>"
        "<li>Architect &amp; maintain distributed payment pipelines.</li>"
        "<li>Mentor junior &amp; mid-level engineers.</li>"
        "</ul>"
        "<br/>"
        "<div>Competitive salary &gt; $150k &lt;market rate&gt;.</div>"
    )
    cleaned = clean_html_description(raw_html)

    assert "About the Role" in cleaned
    assert "We are looking for a Senior Engineer to join our payments team." in cleaned
    assert "• Architect & maintain distributed payment pipelines." in cleaned
    assert "• Mentor junior & mid-level engineers." in cleaned
    assert "Competitive salary > $150k <market rate>." in cleaned
    # Ensure no raw html tags remain
    assert "<" not in cleaned or "<market rate>" in cleaned  # unescaped entity
    assert "<h3>" not in cleaned
    assert "<ul>" not in cleaned
    assert "<li>" not in cleaned


def test_compute_canonical_slug_and_fingerprint_cross_source_equality() -> None:
    # Source A (Greenhouse): Stripe, Inc. | Sr. Software Engineer | San Francisco, CA | REMOTE
    slug_a = compute_canonical_slug(
        company_name="Stripe, Inc.",
        title="Sr. Software Engineer",
        location="San Francisco, CA",
        workplace_type=WorkplaceTypeEnum.REMOTE,
    )
    fp_a = compute_dedup_fingerprint(
        company_name="Stripe, Inc.",
        title="Sr. Software Engineer",
        location="San Francisco, CA",
        workplace_type=WorkplaceTypeEnum.REMOTE,
    )

    # Source B (Lever): Stripe | Senior Software Engineer | San Francisco, CA | REMOTE
    slug_b = compute_canonical_slug(
        company_name="Stripe",
        title="Senior Software Engineer",
        location="San Francisco, CA",
        workplace_type=WorkplaceTypeEnum.REMOTE,
    )
    fp_b = compute_dedup_fingerprint(
        company_name="Stripe",
        title="Senior Software Engineer",
        location="San Francisco, CA",
        workplace_type=WorkplaceTypeEnum.REMOTE,
    )

    assert slug_a == slug_b
    assert slug_a == "stripe:senior-software-engineer:san-francisco-ca:remote"
    assert fp_a == fp_b
    assert len(fp_a) == 64
