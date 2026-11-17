from app.services.url_utils import normalize_domain


def test_strips_scheme_www_path_and_lowercases():
    assert normalize_domain("https://WWW.Example.com/contact") == "example.com"


def test_adds_scheme_when_missing():
    assert normalize_domain("example.co.zw/about") == "example.co.zw"


def test_different_paths_same_domain_collapse():
    assert normalize_domain("https://example.com/a") == normalize_domain("http://example.com/b")


def test_www_and_non_www_match():
    assert normalize_domain("https://www.hotel.co.zw") == normalize_domain("https://hotel.co.zw")
