from urllib.parse import urlparse


def normalize_domain(url: str) -> str:
    """Reduces a URL to a bare host for dedup: strips scheme, 'www.', path,
    and lowercases. 'https://WWW.Example.com/contact' -> 'example.com'."""
    if "://" not in url:
        url = "https://" + url
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host
