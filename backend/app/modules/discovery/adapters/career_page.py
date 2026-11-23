"""Read job listings from an explicitly approved public career page."""

import hashlib
import json
import ssl
from collections.abc import Iterator
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.core.config import get_settings
from app.modules.discovery.adapters.base import DiscoveryResult, JobSourceAdapter, RawDiscoveredJob
from app.modules.discovery.exceptions import (
    InvalidSourceConfigError,
    MalformedPayloadError,
    NetworkTimeoutError,
    NonRetryableDiscoveryError,
    RateLimitExceededError,
    RetryableDiscoveryError,
    SourceNotFoundError,
    UpstreamServerError,
)
from app.modules.discovery.models import JobSourceTypeEnum

MAX_PAGE_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 15
SOURCE_NAME = "Career Page"


class CareerMarkup(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.structured: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._script: list[str] | None = None
        self._link: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._script = []
        if tag == "a" and (href := attributes.get("href")):
            self._link = (href, [])

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script.append(data)
        elif self._link is not None:
            self._link[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script is not None:
            self.structured.append("".join(self._script))
            self._script = None
        if tag == "a" and self._link is not None:
            href, parts = self._link
            self.links.append((href, " ".join("".join(parts).split())))
            self._link = None


def _job_postings(value: Any) -> Iterator[dict[str, Any]]:
    pending = [value]
    while pending:
        node = pending.pop()
        if isinstance(node, list):
            pending.extend(reversed(node))
        elif isinstance(node, dict):
            kinds = node.get("@type", [])
            kinds = kinds if isinstance(kinds, list) else [kinds]
            job_types = (
                "JobPosting",
                "https://schema.org/JobPosting",
                "http://schema.org/JobPosting",
            )
            if any(kind in job_types for kind in kinds):
                yield node
            pending.extend(
                node[key]
                for key in ("@graph", "itemListElement", "item", "mainEntity")
                if key in node
            )


def _same_origin_url(base: str, href: str) -> str | None:
    if any(character in href for character in ("\\", "\r", "\n", "\t")):
        return None
    try:
        url = urlsplit(urljoin(base, href))
        if (
            url.scheme != "https"
            or url.hostname != urlsplit(base).hostname
            or url.port not in (None, 443)
            or url.username is not None
            or url.password is not None
        ):
            return None
    except ValueError:
        return None
    normalized = urlunsplit((url.scheme, url.hostname or "", url.path or "/", url.query, ""))
    return normalized if len(normalized) <= 1024 else None


def _job(url: str, payload: dict[str, Any]) -> RawDiscoveredJob:
    date_posted = payload.get("datePosted")
    return RawDiscoveredJob(
        external_id=hashlib.sha256(url.encode()).hexdigest(),
        source_url=url,
        raw_payload=payload,
        raw_posted_at=date_posted
        if isinstance(date_posted, str) and len(date_posted) <= 100
        else None,
    )


class CareerPageAdapter(JobSourceAdapter):
    @property
    def source_type(self) -> JobSourceTypeEnum:
        return JobSourceTypeEnum.CAREER_PAGE

    def validate_configuration(self, configuration: dict[str, Any]) -> None:
        if configuration.get("permitted") is not True:
            raise InvalidSourceConfigError("Career page discovery requires permitted=true.")
        prefix = configuration.get("job_link_prefix")
        if prefix is not None and (
            not isinstance(prefix, str)
            or len(prefix) > 512
            or not prefix.startswith("/")
            or prefix.startswith("//")
            or any(character in prefix for character in ("?", "#", "\\", "\r", "\n", "\t"))
            or any(part in {".", ".."} for part in prefix.split("/"))
            or prefix == "/"
        ):
            raise InvalidSourceConfigError(
                "Job link prefix must be a specific path such as /careers/jobs/."
            )

    def validate_source(self, base_url: str, configuration: dict[str, Any]) -> None:
        self.validate_configuration(configuration)
        try:
            parsed = urlsplit(base_url)
        except ValueError as exc:
            raise InvalidSourceConfigError("Enter a valid career page URL.") from exc
        allowed = {host.lower() for host in get_settings().career_page_allowed_hosts}
        if parsed.hostname not in allowed or _same_origin_url(base_url, base_url) is None:
            raise InvalidSourceConfigError(
                "Use an HTTPS career page on a host approved by the operator."
            )
        if parsed.fragment:
            raise InvalidSourceConfigError("The career page URL must not include a fragment.")

    async def discover_jobs(
        self,
        base_url: str,
        configuration: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> DiscoveryResult:
        self.validate_source(base_url, configuration)
        if client is None:
            async with httpx.AsyncClient(
                timeout=TIMEOUT_SECONDS, trust_env=False, verify=ssl.create_default_context()
            ) as owned:
                markup = await self._fetch(owned, base_url)
        else:
            markup = await self._fetch(client, base_url)

        page = CareerMarkup()
        page.feed(markup)
        page.close()
        jobs = self._extract_jobs(page, base_url, configuration.get("job_link_prefix"))
        return DiscoveryResult(
            source_identifier=base_url,
            source_type=self.source_type,
            jobs=jobs,
            warnings=[] if jobs else ["No supported job listings found on the configured page."],
        )

    def _extract_jobs(
        self, page: CareerMarkup, base_url: str, prefix: str | None
    ) -> list[RawDiscoveredJob]:
        postings: list[dict[str, Any]] = []
        for script in page.structured:
            try:
                postings.extend(_job_postings(json.loads(script)))
            except (ValueError, RecursionError):
                continue

        jobs: dict[str, RawDiscoveredJob] = {}
        for posting in postings:
            title = posting.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            href = posting.get("url")
            if href is None:
                page_ref = posting.get("mainEntityOfPage")
                href = page_ref.get("@id") if isinstance(page_ref, dict) else page_ref
            if href is None and len(postings) == 1:
                href = base_url
            if isinstance(href, str) and (url := _same_origin_url(base_url, href)):
                jobs[url] = _job(url, posting)

        if prefix:
            path = prefix.rstrip("/")
            for href, title in page.links:
                if not title or not (url := _same_origin_url(base_url, href)):
                    continue
                if urlsplit(url).path.startswith(path + "/") or urlsplit(url).path == path:
                    jobs.setdefault(url, _job(url, {"title": title}))
        return list(jobs.values())

    async def _fetch(self, client: httpx.AsyncClient, url: str) -> str:
        try:
            async with client.stream(
                "GET",
                url,
                follow_redirects=False,
                headers={"Accept": "text/html, application/xhtml+xml"},
            ) as response:
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "")
                    raise RateLimitExceededError(
                        SOURCE_NAME, int(retry_after) if retry_after.isdecimal() else None
                    )
                if response.status_code == 404:
                    raise SourceNotFoundError(SOURCE_NAME, urlsplit(url).path)
                if response.status_code >= 500:
                    raise UpstreamServerError(SOURCE_NAME, response.status_code)
                if response.status_code != 200:
                    raise NonRetryableDiscoveryError(
                        f"The configured career page returned HTTP {response.status_code}. Use the final public URL."
                    )
                content_type = (
                    response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                )
                if content_type not in {"text/html", "application/xhtml+xml"}:
                    raise MalformedPayloadError(SOURCE_NAME, "The page must serve HTML.")
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    body.extend(chunk)
                    if len(body) > MAX_PAGE_BYTES:
                        raise MalformedPayloadError(
                            SOURCE_NAME, "The career page exceeds the size limit."
                        )
                return body.decode(response.encoding or "utf-8", errors="replace")
        except httpx.TimeoutException as exc:
            raise NetworkTimeoutError(SOURCE_NAME, TIMEOUT_SECONDS) from exc
        except httpx.RequestError as exc:
            raise RetryableDiscoveryError("Unable to fetch the configured career page.") from exc
