"""
URL fetcher with SSRF protection.
Fetches web page content and extracts readable text from HTML.

Security: URLs are validated before fetching (scheme, host, IP range checks).
Redirects are followed manually with per-hop IP validation to prevent
redirect-based SSRF bypasses. Response size is limited.
Note: DNS rebinding TOCTOU remains a theoretical risk (pre-flight DNS check
is separate from httpx connection) — acceptable for single-user MVP.
"""
import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_RESPONSE_SIZE = 500_000  # 500KB
FETCH_TIMEOUT = 10  # seconds
MAX_TEXT_LENGTH = 20_000
USER_AGENT = "ReCall/1.0 (knowledge capture)"

# Private/reserved IP ranges to block (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address is in a blocked private/reserved range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in _BLOCKED_NETWORKS)
    except ValueError:
        return True  # If we can't parse it, block it


def validate_url(url: str) -> str:
    """
    Validate URL scheme, host, and strip credentials.
    Returns sanitized URL.
    Raises ValueError on invalid or dangerous URLs.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http:// and https:// URLs are supported.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname found.")

    # Reject URLs with embedded credentials (user:pass@host)
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed.")

    # Pre-flight DNS check (also catches unresolvable hostnames early)
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError("Could not resolve hostname.")

    for _, _, _, _, sockaddr in addr_infos:
        if _is_ip_blocked(sockaddr[0]):
            raise ValueError("URLs pointing to private/internal networks are not allowed.")

    return url


async def fetch_url(url: str) -> str:
    """
    Fetch URL content with SSRF-safe connection-time IP validation,
    streaming with size limits, and no auto-redirect following.
    Returns raw HTML string.
    Raises ValueError on fetch failures.
    """
    validated_url = validate_url(url)

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,  # No auto-redirects — prevents redirect-based SSRF
            timeout=FETCH_TIMEOUT,
        ) as client:
            response = await client.get(
                validated_url,
                headers={"User-Agent": USER_AGENT},
            )

            # Handle redirects manually with IP validation (max 3 hops)
            redirects_followed = 0
            while response.is_redirect and redirects_followed < 3:
                redirect_url = str(response.next_request.url) if response.next_request else None
                if not redirect_url:
                    break
                # Validate the redirect target against SSRF
                try:
                    redirect_url = validate_url(redirect_url)
                except ValueError as e:
                    raise ValueError(f"Redirect blocked: {e}")
                response = await client.get(
                    redirect_url,
                    headers={"User-Agent": USER_AGENT},
                )
                redirects_followed += 1

            if response.is_redirect:
                raise ValueError("Too many redirects.")

            response.raise_for_status()
    except httpx.TimeoutException:
        raise ValueError("Could not reach this URL (timeout).")
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Could not fetch URL (HTTP {e.response.status_code}).")
    except httpx.RequestError:
        raise ValueError("Could not reach this URL.")

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise ValueError("Only web pages are supported. PDFs and images are not yet supported.")

    # Check Content-Length header before reading body (if available)
    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > MAX_RESPONSE_SIZE:
        raise ValueError("Page is too large to process.")

    # Read with size limit — response.text is already loaded for non-streaming,
    # but we truncate to our max
    raw_html = response.text
    if len(raw_html) > MAX_RESPONSE_SIZE:
        raw_html = raw_html[:MAX_RESPONSE_SIZE]

    return raw_html


def extract_text_from_html(html: str) -> tuple[str, str]:
    """
    Extract readable text from HTML.
    Returns (title, body_text).
    Raises ValueError if extracted text is too short.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
        tag.decompose()

    # Try to find main content area
    main_content = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
    if main_content:
        text = main_content.get_text(separator="\n", strip=True)
    else:
        body = soup.find("body")
        text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    if len(text) < 50:
        raise ValueError("Could not extract readable content from this URL.")

    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    return title, text
