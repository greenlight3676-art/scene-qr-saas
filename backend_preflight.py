"""Read-only database/Auth checks. No migrations, emails, Stripe or deployment.

Use the process's private environment; never pass credentials as CLI arguments.
Offline by default. A passed read-only check is not end-to-end acceptance.
"""
import argparse
import json
import os
import re


def result(task, status, detail):
    return {'task': task, 'status': status, 'detail': detail}


def database_check(online=False):
    url = os.getenv('SCENE_DATABASE_URL', '')
    if not url:
        return result('database', 'blocked', 'Restricted SCENE_DATABASE_URL is missing')
    if not online:
        return result('database', 'not_run', 'Configured; use --online for read-only runtime role, TLS and schema checks')
    try:
        from storage import verify_postgres
        # Existing startup validator only reads metadata; it never migrates.
        verify_postgres(url)
    except Exception:
        # Provider/driver errors may contain passwords, URLs or certificate paths.
        return result('database', 'blocked', 'Connection or runtime role/TLS/schema verification failed; inspect private configuration')
    return result('database', 'verified_read_only', 'Runtime role, required TLS configuration, RLS flags and schema version checked; workflows/restore not tested')


def auth_check(online=False):
    if os.getenv('SCENE_AUTH_MODE') != 'supabase':
        return result('auth', 'blocked', 'SCENE_AUTH_MODE must be supabase for this check')
    try:
        import managed_auth
        managed_auth.validate_config()
    except Exception:
        return result('auth', 'blocked', 'Managed Auth requires publishable key, secure cookies and no demo mode')
    if not online:
        return result('auth', 'not_run', 'Configured; use --online to read the provider confirmation policy')
    try:
        managed_auth.require_email_confirmation()
    except Exception:
        return result('auth', 'blocked', 'Provider policy unavailable or email confirmation/email login policy failed')
    return result('auth', 'verified_read_only', 'Provider requires email confirmation and enables email login; delivery/login/recovery not tested')


def mail_check():
    sender = os.getenv('SCENE_MAIL_FROM', '')
    key = os.getenv('SCENE_RESEND_API_KEY', '')
    if not key.startswith('re_') or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', sender):
        return result('mail', 'blocked', 'Verified sender and private Resend credentials are missing or invalid')
    return result('mail', 'not_run', 'Configuration present; DNS, approved test recipient and actual delivery acceptance still required; no mail sent')


def run(check='all', online=False):
    checks = {'database': lambda: database_check(online),
              'auth': lambda: auth_check(online), 'mail': mail_check}
    return [fn() for name, fn in checks.items() if check in ('all', name)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', choices=('all', 'database', 'auth', 'mail'), default='all')
    parser.add_argument('--online', action='store_true', help='Allow read-only database/Auth network checks only')
    args = parser.parse_args(argv)
    checks = run(args.check, args.online)
    print(json.dumps({'checks': checks, 'scope': 'read-only; no end-to-end acceptance'}, indent=2))
    return 0 if all(row['status'] == 'verified_read_only' for row in checks) else 2


if __name__ == '__main__':
    raise SystemExit(main())
