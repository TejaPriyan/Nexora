# Security & Privacy Policy

NEXORA is designed local-first and privacy-first. This document states the
principles every module -- shipped or planned -- is expected to follow, and
how to report a security issue.

## Principles

1. **No hidden capture, ever.** No module may record the screen, keyboard,
   audio, or any other input/output channel without an explicit,
   caller-initiated permission grant (see `nexora.security.PermissionManager`).
   There is no "implied consent" in NEXORA.
2. **Telemetry and cloud sync default to off.** `Config.telemetry` and
   `Config.cloud_sync` default to `False`. Nothing in NEXORA core makes a
   network call.
3. **Explicit permission scopes, always audited.** Every grant and revoke
   made through `PermissionManager` is recorded with a reason and
   timestamp, retrievable via `.audit_trail()`.
4. **Secrets are not blindly serialized.** State/timeline snapshots run
   through `nexora.security.SecretRedactor`, which redacts obvious
   secret-shaped keys (password, token, api_key, etc.) by default and
   supports explicit `.ignore(...)` additions. This is a best-effort
   heuristic, not a guarantee -- do not rely on it as your only line of
   defense for genuinely sensitive data.
5. **Sandboxes are never claimed to be perfectly secure.** The
   AgentBox module documents its actual isolation guarantees and
   known limitations in `docs/ARCHITECTURE.md` rather than implying full containment.
6. **Local by default.** `nexora.storage.LocalStore` persists to disk
   (SQLite) under the user's home directory and makes no network calls.

## Reporting a vulnerability

Please do not open a public GitHub issue for security reports.

Instead, email **security@nexora.dev** (or open a private security advisory on GitHub) with:

- A description of the issue and its potential impact
- Steps to reproduce, or a minimal proof of concept
- The NEXORA version (`nexora version`) and Python version affected

We aim to acknowledge reports within 5 business days.

## Supported versions

Starting with NEXORA 1.0.0, the current release series (1.0.x) is
actively supported with security fixes.
