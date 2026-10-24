"""Two-business acceptance and restored API checks on disposable test data only."""
import secrets
import pytest
from fastapi.testclient import TestClient
from test_api import registration
from backup import backup_sqlite
import server


def two_business_workflow(monkeypatch):
    monkeypatch.setenv('SCENE_REQUIRE_GUEST_SESSION', '1')
    suffix = secrets.token_hex(6)
    states = []
    for label, status in (('alpha', 'completed'), ('beta', 'in_progress')):
        owner, guest = TestClient(server.app), TestClient(server.app)
        slug, headers = registration(owner, f'{label}-{suffix}@example.invalid',
                                     f'Acceptance {label} {suffix}')
        board = owner.get(f'/api/admin/{slug}').json()
        station = board['stations'][0]
        token = station['token']
        png = guest.get(f'/api/qr/{token}.png')
        assert png.status_code == 200 and png.content.startswith(b'\x89PNG')
        catalog = guest.get(f'/api/q/{token}')
        assert catalog.status_code == 200 and catalog.json()['slug'] == slug
        session = guest.post(f'/api/q/{token}/session')
        assert session.status_code == 201, session.text
        guest_headers = {'x-scene-guest': session.json()['guest_token']}
        contact = f'guest-{label}-{suffix}@example.invalid'
        body = {'kind': 'question', 'message': f'Synthetic {label} quote request',
                'customer_name': f'Synthetic {label}', 'customer_contact': contact,
                'reply_consent': True, 'client_key': secrets.token_hex(16)}
        submitted = guest.post(f'/api/q/{token}/requests', json=body, headers=guest_headers)
        assert submitted.status_code == 200, submitted.text
        rid, ticket = submitted.json()['request_id'], submitted.json()['ticket']
        assert owner.patch(f'/api/admin/{slug}/requests/{rid}', headers=headers,
                           json={'status': status}).status_code == 200
        state = dict(owner=owner, guest=guest, slug=slug, headers=headers, token=token,
                     rid=rid, ticket=ticket, status=status, contact=contact,
                     guest_headers=guest_headers, body=body)
        states.append(state)
    assert_isolated(states)
    # Guest sessions are bound to their QR location even when both are valid.
    a, b = states
    response = a['guest'].post(f'/api/q/{b["token"]}/requests', json=b['body'],
                               headers=a['guest_headers'])
    assert response.status_code == 401
    return states


def assert_isolated(states):
    for own, other in (states, states[::-1]):
        owner, guest, slug, rid = own['owner'], own['guest'], own['slug'], own['rid']
        board = owner.get(f'/api/admin/{slug}')
        assert board.status_code == 200
        requests = board.json()['requests']
        assert {r['id'] for r in requests} == {rid}
        assert requests[0]['status'] == own['status']
        assert requests[0]['customer_contact'] == own['contact']
        assert other['contact'] not in board.text
        assert owner.get(f'/api/admin/{other["slug"]}').status_code == 404
        assert owner.get(f'/api/admin/{other["slug"]}/customers').status_code == 404
        for target_slug in (slug, other['slug']):
            assert owner.patch(f'/api/admin/{target_slug}/requests/{other["rid"]}',
                               headers=own['headers'], json={'status': 'completed'}).status_code == 404
        receipt = f'/api/guest/requests/{rid}'
        assert guest.get(receipt).status_code == 401
        assert guest.get(receipt, headers={'x-scene-ticket': other['ticket']}).status_code == 404
        result = guest.get(receipt, headers={'x-scene-ticket': own['ticket']})
        assert result.status_code == 200 and result.json()['status'] == own['status']
        assert own['contact'] not in result.text
        catalog = guest.get(f'/api/q/{own["token"]}')
        assert catalog.status_code == 200 and own['contact'] not in catalog.text
        assert guest.get(f'/api/admin/{slug}').status_code == 401


def test_two_business_qr_requests_and_bidirectional_isolation(monkeypatch):
    two_business_workflow(monkeypatch)


def test_two_business_sqlite_restore_preserves_api_workflow(monkeypatch, tmp_path):
    if server.DATABASE_URL:
        pytest.skip('SQLite recovery; PostgreSQL dump/restore runs separately')
    states = two_business_workflow(monkeypatch)
    snapshot, restored = tmp_path / 'snapshot.sqlite', tmp_path / 'restored.sqlite'
    backup_sqlite(server.DB_PATH, snapshot)
    # A later source write must not leak into the earlier recovery point.
    b = states[1]
    assert b['owner'].patch(f'/api/admin/{b["slug"]}/requests/{b["rid"]}',
                            headers=b['headers'], json={'status': 'completed'}).status_code == 200
    backup_sqlite(snapshot, restored)
    monkeypatch.setattr(server, 'DB_PATH', restored)
    assert_isolated(states)
    # Saved guest capability, receipt and session still work against the restore.
    duplicate = b['guest'].post(f'/api/q/{b["token"]}/requests', json=b['body'],
        headers={**b['guest_headers'], 'x-scene-ticket': b['ticket']})
    assert duplicate.status_code == 200 and duplicate.json()['already_sent'] is True
    assert duplicate.json()['request_id'] == b['rid']
    assert b['owner'].patch(f'/api/admin/{b["slug"]}/requests/{b["rid"]}',
                            headers=b['headers'], json={'status': 'completed'}).status_code == 200
    b['status'] = 'completed'
    assert_isolated(states)
