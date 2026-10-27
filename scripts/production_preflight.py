#!/usr/bin/env python3
"""Read-only Scene QR production preflight. Never prints credential values.

Usage:
  SCENE_PUBLIC_URL=https://your-site.example \
  SCENE_API_BASE_URL=https://your-api.example \
  SCENE_SUPABASE_URL=https://your-project.supabase.co \
  python3 scripts/production_preflight.py

No database writes, authentication attempts, or guest requests are performed.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def check_url(name):
    value = os.getenv(name, "").strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        print(f"FAIL {name}: provide an HTTPS URL without embedded credentials")
        return None
    print(f"PASS {name}: valid HTTPS URL")
    return value


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "scene-preflight/1"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read(2048)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read(2048)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"FAIL connectivity: {type(exc).__name__}")
        return None, "", b""


def main():
    print("SCENE QR read-only production preflight")
    site = check_url("SCENE_PUBLIC_URL")
    api = check_url("SCENE_API_BASE_URL")
    supabase = check_url("SCENE_SUPABASE_URL")
    if not all((site, api, supabase)):
        return 2
    if urllib.parse.urlparse(api).hostname == urllib.parse.urlparse(supabase).hostname:
        print("WARN API URL equals Supabase project URL: verify a real API gateway exists; database/Auth alone do not implement FastAPI /api routes")
    failures = 0
    for label, url, expected in (
        ("frontend", site + "/", {200}),
        ("backend readiness", api + "/readyz", {200}),
        ("authentication route", api + "/api/me", {200, 401, 403}),
    ):
        status, mime, body = get(url)
        if status not in expected:
            print(f"FAIL {label}: HTTP {status or 'unreachable'} (expected {sorted(expected)})")
            failures += 1
            continue
        if label == "backend readiness":
            try:
                data = json.loads(body)
                if data.get("ok") is not True:
                    print("FAIL backend readiness: response lacks ok=true")
                    failures += 1
                    continue
            except (ValueError, AttributeError):
                print("FAIL backend readiness: invalid JSON")
                failures += 1
                continue
        if label == "authentication route" and "text/html" in mime.lower():
            print("FAIL authentication route: HTML fallback instead of API response")
            failures += 1
            continue
        print(f"PASS {label}: HTTP {status}")
    print("NOTE: This does not verify RLS isolation, auth delivery, billing, backups, or physical QR tests.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
