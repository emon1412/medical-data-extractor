"""Add baseline security headers to every response.

Conservative defaults that are safe for an API that also serves a static SPA:
  - X-Content-Type-Options: nosniff           (block MIME sniffing)
  - X-Frame-Options: DENY                     (prevent clickjacking; the SPA
                                               isn't meant to be iframed)
  - Referrer-Policy: strict-origin-when-cross-origin
  - Strict-Transport-Security                 (HTTPS-only, only when on TLS)
  - Permissions-Policy                        (deny unused powerful features)
  - Cross-Origin-Opener-Policy: same-origin   (mitigate XS-Leaks)
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


# Disable powerful browser features we never use. Keeps an attacker who lands
# script execution from accessing camera / mic / geolocation / etc.
_PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
    "microphone=(), midi=(), payment=(), usb=(), magnetometer=(), "
    "picture-in-picture=(), interest-cohort=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        headers = response.headers

        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", _PERMISSIONS_POLICY)
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        # Only assert HSTS on HTTPS — sending it on http://localhost would
        # break local development on shared machines.
        scheme = request.url.scheme
        forwarded_proto = request.headers.get("x-forwarded-proto", scheme)
        if forwarded_proto == "https":
            headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )

        return response
