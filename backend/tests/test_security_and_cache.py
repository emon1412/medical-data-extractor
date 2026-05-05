"""Tests for the security-headers middleware and the extraction cache."""
from app.services.extraction_cache import extraction_cache


def test_security_headers_present_on_every_response(client):
    r = client.get("/api/v1/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in r.headers
    assert r.headers.get("Cross-Origin-Opener-Policy") == "same-origin"


def test_hsts_only_set_on_https(client):
    """HSTS would break http://localhost dev. The middleware only adds it
    when the request scheme (or X-Forwarded-Proto from a TLS terminator) is
    https. The TestClient defaults to http, so HSTS should be absent."""
    r = client.get("/api/v1/health")
    assert "Strict-Transport-Security" not in r.headers


def test_extraction_cache_lru_behaviour():
    from app.schemas.extraction import PatientExtraction

    extraction_cache.clear()
    pe = PatientExtraction(
        first_name="A", last_name="B", date_of_birth=None, confidence="high", source="llm"
    )
    extraction_cache.put("k1", pe)
    assert extraction_cache.size == 1

    cached = extraction_cache.get("k1")
    assert cached is not None
    assert cached.first_name == "A"

    # Mutating the returned copy must not affect what's stored
    cached.first_name = "MUTATED"
    again = extraction_cache.get("k1")
    assert again is not None
    assert again.first_name == "A"

    assert extraction_cache.get("does-not-exist") is None
