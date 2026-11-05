"""Deterministic slug formulation, URL sanitization, and canonical deduplication algorithms."""

import hashlib
import html
import re
import urllib.parse

from app.modules.candidate.models import WorkplaceTypeEnum

# Corporate legal suffix regex (whole words, case-insensitive)
CORPORATE_SUFFIXES_PATTERN = re.compile(
    r"\b(inc|incorporated|corp|corporation|llc|ltd|limited|technologies|solutions|group|holdings)\b\.?",
    re.IGNORECASE,
)

# Common title abbreviations to expand deterministically
TITLE_ABBREVIATIONS = [
    (re.compile(r"\bsr\b\.?", re.IGNORECASE), "senior"),
    (re.compile(r"\bjr\b\.?", re.IGNORECASE), "junior"),
    (re.compile(r"\bsw\s+eng\b\.?", re.IGNORECASE), "software engineer"),
    (re.compile(r"\bswe\b\.?", re.IGNORECASE), "software engineer"),
    (re.compile(r"\bqa\b\.?", re.IGNORECASE), "quality assurance"),
    (re.compile(r"\bml\b\.?", re.IGNORECASE), "machine learning"),
    (re.compile(r"\bai\b\.?", re.IGNORECASE), "artificial intelligence"),
]

# Query parameters stripped during URL canonicalization
TRACKING_PARAMS_PATTERN = re.compile(
    r"^(utm_.*|gh_jid|lever-origin|lever-source|ref|source|fbclid|gclid|token|sid|_hsenc|_hsmi|mc_cid|mc_eid)$",
    re.IGNORECASE,
)


def normalize_slug(text: str) -> str:
    """Normalize freeform text into a stable, deterministic comparison slug.

    Rules matching technical design TD-004:
    1. Converts to lowercase.
    2. Strips corporate suffixes: 'inc', 'corp', 'llc', 'ltd', 'technologies', etc.
    3. Expands common title abbreviations: 'sr' -> 'senior', 'jr' -> 'junior', 'swe' -> 'software engineer'.
    4. Removes non-alphanumeric characters (except spaces).
    5. Normalizes internal whitespace to single hyphens '-'.
    6. Trims leading and trailing hyphens.
    """
    if not text or not text.strip():
        return ""

    lowered = text.lower().strip()

    # Strip corporate suffixes
    cleaned = CORPORATE_SUFFIXES_PATTERN.sub("", lowered)

    # Expand title abbreviations
    for pattern, replacement in TITLE_ABBREVIATIONS:
        cleaned = pattern.sub(replacement, cleaned)

    # Remove non-alphanumeric characters (keep alphanumeric and spaces)
    alphanumeric = re.sub(r"[^a-z0-9\s]", " ", cleaned)

    # Collapse multiple spaces and replace with hyphens
    slug = re.sub(r"\s+", "-", alphanumeric.strip())

    # Remove multiple adjacent hyphens and strip ends
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def sanitize_application_url(url: str) -> str:
    """Sanitize and canonicalize application URLs.

    Rules matching technical design TD-004:
    1. Strip tracking query parameters matching:
       utm_*, gh_jid, lever-origin, lever-source, ref, source, fbclid, gclid, token, sid.
    2. Convert domain and path to lowercase.
    3. Remove trailing slashes and default document names (e.g. index.html).
    4. Enforce https:// protocol.
    """
    if not url or not url.strip():
        return ""

    raw_url = url.strip()
    parsed = urllib.parse.urlparse(raw_url)

    # 1. Enforce HTTPS scheme
    scheme = "https"

    # 2. Lowercase domain
    netloc = parsed.netloc.lower()

    # 3. Lowercase path & strip trailing slash and default document names
    path = parsed.path.lower()
    path = re.sub(r"/(index|default)\.(html?|php|asp[x]?)$", "", path)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # 4. Filter query parameters
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    filtered_params = [(k, v) for k, v in query_params if not TRACKING_PARAMS_PATTERN.match(k)]
    # Sort remaining query parameters for deterministic representation
    filtered_params.sort(key=lambda pair: pair[0])
    query = urllib.parse.urlencode(filtered_params)

    # Reconstruct canonical URL (discard fragments)
    return urllib.parse.urlunparse((scheme, netloc, path, "", query, ""))


def clean_html_description(html_content: str) -> str:
    """Safely convert HTML job description into clean, readable plaintext.

    Preserves paragraph breaks, headings, and list bullets without altering semantic requirements.
    Does NOT use an LLM.
    """
    if not html_content or not html_content.strip():
        return ""

    raw = html_content.strip()

    # Replace breaks and paragraph/header closings with newlines
    raw = re.sub(r"<(br|hr)\s*/?>", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"</(p|div|tr|h[1-6])>", "\n\n", raw, flags=re.IGNORECASE)

    # Replace list items with clean bullets
    raw = re.sub(r"<li[^>]*>", "\n• ", raw, flags=re.IGNORECASE)
    raw = re.sub(r"</li>", "", raw, flags=re.IGNORECASE)

    # Strip remaining HTML tags
    clean = re.sub(r"<[^>]+>", "", raw)

    # Unescape HTML entities (e.g. &amp;, &lt;, &gt;, &quot;)
    unescaped = html.unescape(clean)

    # Normalize carriage returns and tabs
    normalized = unescaped.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")

    # Collapse repeated horizontal whitespace
    normalized = re.sub(r"[ \t]+", " ", normalized)

    # Collapse excessive blank lines to at most double newlines
    normalized = re.sub(r"\n\s*\n\s*\n+", "\n\n", normalized)

    return normalized.strip()


def compute_canonical_slug(
    company_name: str,
    title: str,
    location: str | None,
    workplace_type: WorkplaceTypeEnum,
) -> str:
    """Compute the deterministic slug string for cross-source canonical comparison."""
    company_slug = normalize_slug(company_name)
    title_slug = normalize_slug(title)
    location_slug = normalize_slug(location or "")
    workplace_slug = workplace_type.value.lower()
    return f"{company_slug}:{title_slug}:{location_slug}:{workplace_slug}"


def compute_dedup_fingerprint(
    company_name: str,
    title: str,
    location: str | None,
    workplace_type: WorkplaceTypeEnum,
) -> str:
    """Compute the deterministic SHA-256 fingerprint for canonical deduplication."""
    slug = compute_canonical_slug(company_name, title, location, workplace_type)
    return hashlib.sha256(slug.encode("utf-8")).hexdigest()
