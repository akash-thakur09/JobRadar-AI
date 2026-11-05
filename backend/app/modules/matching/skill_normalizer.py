"""Skill normalization engine, taxonomy dictionary, and text extraction."""

import re

# Canonical skill taxonomy mapping raw aliases and common abbreviations to canonical keys
SKILL_ALIASES: dict[str, str] = {
    # Languages & Runtimes
    "python": "python",
    "py": "python",
    "python3": "python",
    "javascript": "javascript",
    "js": "javascript",
    "ecmascript": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "golang": "go",
    "go language": "go",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "c++": "cpp",
    "cpp": "cpp",
    "c#": "csharp",
    "csharp": "csharp",
    "c sharp": "csharp",
    ".net": "dotnet",
    "dotnet": "dotnet",
    "dot net": "dotnet",
    "ruby": "ruby",
    "ruby on rails": "ruby",
    "rails": "ruby",
    "scala": "scala",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
    "sql": "sql",
    "nosql": "nosql",
    # Frameworks & Libraries
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "react native": "react_native",
    "react-native": "react_native",
    "node": "nodejs",
    "nodejs": "nodejs",
    "node.js": "nodejs",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "express": "express",
    "expressjs": "express",
    "express.js": "express",
    "nextjs": "nextjs",
    "next.js": "nextjs",
    "vue": "vue",
    "vuejs": "vue",
    "vue.js": "vue",
    "angular": "angular",
    "angularjs": "angular",
    "html": "html",
    "html5": "html",
    "css": "css",
    "css3": "css",
    "tailwind": "tailwind",
    "tailwindcss": "tailwind",
    "tailwind css": "tailwind",
    # Databases & Storage
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "psql": "postgresql",
    "pgsql": "postgresql",
    "mysql": "mysql",
    "redis": "redis",
    "mongodb": "mongodb",
    "mongo": "mongodb",
    "sqlite": "sqlite",
    "elasticsearch": "elasticsearch",
    "elastic search": "elasticsearch",
    "cassandra": "cassandra",
    "dynamodb": "dynamodb",
    # Cloud & Infrastructure
    "aws": "aws",
    "amazon web services": "aws",
    "amazon aws": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "azure": "azure",
    "microsoft azure": "azure",
    "docker": "docker",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "terraform": "terraform",
    "ansible": "ansible",
    "linux": "linux",
    "unix": "linux",
    "ci/cd": "cicd",
    "cicd": "cicd",
    "continuous integration": "cicd",
    "git": "git",
    "github": "git",
    "gitlab": "git",
    # Messaging & Architecture
    "kafka": "kafka",
    "apache kafka": "kafka",
    "rabbitmq": "rabbitmq",
    "celery": "celery",
    "graphql": "graphql",
    "rest api": "rest_apis",
    "restful api": "rest_apis",
    "restful apis": "rest_apis",
    "rest apis": "rest_apis",
    "restful web services": "rest_apis",
    "rest": "rest_apis",
    "grpc": "grpc",
    "microservices": "microservices",
    # Data & ML
    "pandas": "pandas",
    "numpy": "numpy",
    "scikit-learn": "scikit_learn",
    "sklearn": "scikit_learn",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "tensorflow": "tensorflow",
    "tf": "tensorflow",
}

# Special tokens that need specific regex handling to avoid false substring matches
SHORT_WORD_SKILLS = {"go", "ts", "js", "py", "sql", "git", "aws", "gcp", "css"}


def normalize_skill_token(raw_skill: str) -> str:
    """Normalize a raw skill string to its canonical taxonomy key.

    Rules:
    - Lowercase and trim whitespace.
    - Transform special symbols (.e.g C++ -> cpp, C# -> csharp).
    - Map to canonical alias dictionary.
    """
    if not raw_skill or not raw_skill.strip():
        return ""

    cleaned = raw_skill.strip().lower()

    # Exact alias match first
    if cleaned in SKILL_ALIASES:
        return SKILL_ALIASES[cleaned]

    # Handle C++ / C# / .NET
    if cleaned in ("c++", "cpp"):
        return "cpp"
    if cleaned in ("c#", "csharp", "c sharp"):
        return "csharp"
    if cleaned in (".net", "dotnet"):
        return "dotnet"

    # Replace hyphens, underscores, dots with spaces or strip
    simplified = cleaned.replace(".js", "js").replace("-", " ").replace("_", " ")
    simplified = re.sub(r"[^a-z0-9\s\+]", "", simplified).strip()

    if simplified in SKILL_ALIASES:
        return SKILL_ALIASES[simplified]

    # Return sanitized single token
    return re.sub(r"\s+", "_", simplified)


def normalize_skill_set(skills: list[str]) -> set[str]:
    """Convert an arbitrary collection of skill names into a deduplicated canonical skill set."""
    normalized: set[str] = set()
    for s in skills:
        canon = normalize_skill_token(s)
        if canon:
            normalized.add(canon)
    return normalized


def extract_skills_from_text(text: str) -> set[str]:
    """Scan freeform text (job description, title, requirements) and extract canonical skills.

    Uses word-boundary regex patterns to avoid false substring matches.
    """
    if not text or not text.strip():
        return set()

    found_skills: set[str] = set()
    lowered_text = text.lower()

    # Sort aliases by descending length so multi-word aliases match before sub-tokens
    sorted_aliases = sorted(SKILL_ALIASES.keys(), key=len, reverse=True)

    for alias in sorted_aliases:
        # Multi-word alias or special symbols
        if " " in alias or "+" in alias or "#" in alias or "." in alias or "/" in alias:
            escaped = re.escape(alias)
            pattern = rf"(?:\b|(?<=\s)){escaped}(?:\b|(?=\s|[,\.;:\)]))"
            if re.search(pattern, lowered_text):
                found_skills.add(SKILL_ALIASES[alias])
        elif alias in SHORT_WORD_SKILLS:
            # Strict word boundary for short tokens (e.g. \bgo\b must not match "algorithm" or "good")
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered_text):
                found_skills.add(SKILL_ALIASES[alias])
        else:
            # Standard word boundary check
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered_text):
                found_skills.add(SKILL_ALIASES[alias])

    return found_skills
