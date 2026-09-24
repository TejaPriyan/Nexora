# Contributing to NEXORA

Thank you for considering a contribution! NEXORA is built **incrementally**
-- please read this before opening a large PR.

## The one rule that matters most

> Every change must leave the repository in a runnable, tested state.

Concretely:

- `pytest` must pass after your change.
- If you touch `nexora.App`'s public surface, the examples in
  `examples/` must still run (`python examples/basic_app.py`, etc.).
- Do not implement "half" of a feature module and leave the other half
  faked or hard-coded. If a module isn't finished, it stays registered as
  a `PlannedPlugin` (see `nexora/plugins/registry.py`) with an honest,
  descriptive `NotImplementedError` -- never a silent no-op and never
  fabricated output.

## Adding a new feature module

Modules land one at a time, following `docs/ROADMAP.md`. To pick up the
next milestone:

1. Read that milestone's section in `docs/ROADMAP.md`.
2. Implement the module under `src/nexora/<module_name>/`, as a real
   `nexora.plugins.Plugin` subclass (not `PlannedPlugin`).
3. Update `src/nexora/plugins/registry.py` to point that feature name at
   your new class instead of the `_planned(...)` placeholder.
4. Add tests under `tests/` covering the new module's public API.
5. Update the feature-status table in `README.md` and the corresponding
   section of `docs/ARCHITECTURE.md`.
6. If the module needs new third-party dependencies, add them as an
   optional extra in `pyproject.toml` (`[project.optional-dependencies]`)
   -- the base install must stay dependency-free.
7. Any privacy-sensitive capability (screen access, filesystem access
   beyond the project sandbox, network access, etc.) must be gated behind
   `nexora.security.PermissionManager.require(...)`.

## Development setup

```bash
git clone https://github.com/TejaPriyan/Nexora.git
cd Nexora
pip install -e ".[dev]"
pytest
```

## Code style

- Type hints on public functions/methods.
- Prefer explicit, small, well-named functions over clever one-liners.
- New public behavior needs a test; bug fixes need a regression test.

## Reporting bugs / requesting features

Open a GitHub issue. For security issues, see `SECURITY.md` instead --
please do not file those publicly.
