"""Unit tests for Skill Normalizer taxonomy and keyword extraction."""

from app.modules.matching.skill_normalizer import (
    extract_skills_from_text,
    normalize_skill_set,
    normalize_skill_token,
)


def test_normalize_skill_token_aliases() -> None:
    # Casing and punctuation
    assert normalize_skill_token("React.js") == "react"
    assert normalize_skill_token("ReactJS") == "react"
    assert normalize_skill_token("react") == "react"

    # Databases
    assert normalize_skill_token("PostgreSQL") == "postgresql"
    assert normalize_skill_token("Postgres") == "postgresql"
    assert normalize_skill_token("psql") == "postgresql"

    # Cloud & DevOps
    assert normalize_skill_token("AWS") == "aws"
    assert normalize_skill_token("Amazon Web Services") == "aws"
    assert normalize_skill_token("k8s") == "kubernetes"
    assert normalize_skill_token("Kubernetes") == "kubernetes"

    # Languages & Runtimes
    assert normalize_skill_token("Golang") == "go"
    assert normalize_skill_token("Go Language") == "go"
    assert normalize_skill_token("TypeScript") == "typescript"
    assert normalize_skill_token("TS") == "typescript"
    assert normalize_skill_token("Node.js") == "nodejs"
    assert normalize_skill_token("NodeJS") == "nodejs"
    assert normalize_skill_token("C++") == "cpp"
    assert normalize_skill_token("C#") == "csharp"
    assert normalize_skill_token(".NET") == "dotnet"


def test_normalize_skill_set_deduplicates_aliases() -> None:
    raw_skills = ["React.js", "React", "reactjs", "Postgres", "postgresql", "Python", "Docker"]
    normalized = normalize_skill_set(raw_skills)
    assert normalized == {"react", "postgresql", "python", "docker"}


def test_extract_skills_from_text() -> None:
    text = (
        "We are hiring a Senior Backend Engineer to build APIs using Python, FastAPI, and PostgreSQL. "
        "Experience with Docker, Kubernetes (k8s), and Redis is required. "
        "Nice to have: React or TypeScript for occasional frontend work."
    )
    skills = extract_skills_from_text(text)

    expected = {
        "python",
        "fastapi",
        "postgresql",
        "docker",
        "kubernetes",
        "redis",
        "react",
        "typescript",
    }
    for exp in expected:
        assert exp in skills


def test_extract_skills_word_boundary_edge_cases() -> None:
    # "go" must NOT match "algorithm", "good", "category", "negotiation"
    text_without_go = "This is a good algorithm in the category of fast negotiations."
    skills = extract_skills_from_text(text_without_go)
    assert "go" not in skills

    # "go" SHOULD match exact word "Go" or "Golang"
    text_with_go = "Requirements: 3+ years experience with Go and Docker."
    skills_with_go = extract_skills_from_text(text_with_go)
    assert "go" in skills_with_go
    assert "docker" in skills_with_go

    # "java" must NOT match "JavaScript"
    text_js_only = "We build frontend user interfaces using modern JavaScript and React."
    skills_js = extract_skills_from_text(text_js_only)
    assert "javascript" in skills_js
    assert "java" not in skills_js

    # "java" SHOULD match when Java is specified
    text_java_and_js = (
        "Full stack role requiring Java on the backend and JavaScript on the frontend."
    )
    skills_both = extract_skills_from_text(text_java_and_js)
    assert "java" in skills_both
    assert "javascript" in skills_both
