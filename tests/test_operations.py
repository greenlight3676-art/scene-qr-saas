"""Configuration boundaries and safe operational behavior."""
import pytest
from fastapi.testclient import TestClient
from test_api import registration
import server
import operations


def test_production_config_fails_closed(monkeypatch):
    monkeypatch.setenv('SCENE_ENV','production')
    monkeypatch.setenv('SCENE_AUTH_MODE','local')
    with pytest.raises(RuntimeError):operations.validate_environment()
    monkeypatch.setenv('SCENE_AUTH_MODE','supabase')
    monkeypatch.setenv('SCENE_SUPABASE_PUBLISHABLE_KEY','sb_publishable_synthetic_never_real')
    monkeypatch.setenv('SCENE_SECURE_COOKIE','1');monkeypatch.setenv('SCENE_DEMO','0')
    monkeypatch.setenv('SCENE_PUBLIC_URL','https://scene.example.invalid')
    monkeypatch.setenv('SCENE_DATABASE_URL','postgresql://runtime@localhost/scene_test')
    monkeypatch.setenv('SCENE_TRUSTED_HOSTS','scene.example.invalid')
    monkeypatch.setenv('SCENE_REQUIRE_GUEST_SESSION','1');monkeypatch.setenv('SCENE_REQUIRE_SUBSCRIPTION','1')
    operations.validate_environment()
    monkeypatch.delenv('SCENE_PILOT_WITHOUT_BILLING', raising=False)
    monkeypatch.setenv('SCENE_REQUIRE_SUBSCRIPTION','0')
    with pytest.raises(RuntimeError,match='subscription enforcement'):
        operations.validate_environment()
    monkeypatch.setenv('SCENE_PILOT_WITHOUT_BILLING','1')
    operations.validate_environment()
    monkeypatch.setenv('SCENE_REQUIRE_GUEST_SESSION','0')
    with pytest.raises(RuntimeError,match='guest session enforcement'):
        operations.validate_environment()
    monkeypatch.setenv('SCENE_REQUIRE_GUEST_SESSION','1')
    monkeypatch.setenv('SCENE_PILOT_WITHOUT_BILLING','true')
    with pytest.raises(RuntimeError,match='no-billing pilot'):
        operations.validate_environment()
    monkeypatch.setenv('SCENE_PILOT_WITHOUT_BILLING','1')
    monkeypatch.setenv('SCENE_TRUSTED_HOSTS','*')
    with pytest.raises(RuntimeError,match='trusted hosts'):operations.validate_environment()


def test_request_logs_omit_private_input_paths_and_query(caplog):
    caplog.set_level('INFO',logger='scene.http')
    client=TestClient(server.app)
    client.post('/api/auth/login?private=secret-query',json={'email':'private@example.invalid','password':'secret-synthetic-password'})
    text=caplog.text
    assert 'secret-query' not in text and 'secret-synthetic-password' not in text and 'private@example.invalid' not in text
    assert '/api/auth/login' in text and 'request_id' in text


def test_readiness_failure_is_sanitized(monkeypatch):
    from contextlib import contextmanager
    @contextmanager
    def unavailable():raise RuntimeError('private connection secret');yield
    monkeypatch.setattr(server,'db',unavailable)
    response=TestClient(server.app).get('/readyz')
    assert response.status_code==503 and response.json()=={'ok':False}
