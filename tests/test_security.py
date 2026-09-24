import pytest

from nexora.security import PermissionDenied, PermissionManager, SecretRedactor


def test_permission_denied_by_default():
    pm = PermissionManager()
    with pytest.raises(PermissionDenied):
        pm.require("vision.screenshot")


def test_permission_grant_and_require():
    pm = PermissionManager()
    pm.grant("vision.screenshot", reason="user clicked allow")
    pm.require("vision.screenshot")
    assert pm.is_granted("vision.screenshot") is True
    assert len(pm.audit_trail()) == 1


def test_permission_revoke():
    pm = PermissionManager()
    pm.grant("x")
    pm.revoke("x")
    assert pm.is_granted("x") is False
    with pytest.raises(PermissionDenied):
        pm.require("x")


def test_redactor_default_keys():
    r = SecretRedactor()
    data = {"username": "alice", "password": "hunter2", "nested": {"api_key": "abc"}}
    redacted = r.redact(data)
    assert redacted["username"] == "alice"
    assert redacted["password"] == "***REDACTED***"
    assert redacted["nested"]["api_key"] == "***REDACTED***"


def test_redactor_explicit_ignore():
    r = SecretRedactor().ignore("ssn_custom")
    data = {"ssn_custom": "123-45-6789", "other": "fine"}
    redacted = r.redact(data)
    assert redacted["ssn_custom"] == "***REDACTED***"
    assert redacted["other"] == "fine"
