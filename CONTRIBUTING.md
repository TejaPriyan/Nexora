# Contributing to NEXORA

Thank you for considering a contribution! NEXORA is built **incrementally** — please read this before opening a large PR.

---

## 📋 Table of Contents

- [The One Rule That Matters Most](#the-one-rule-that-matters-most)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [Adding a New Feature Module](#-adding-a-new-feature-module)
- [Code Style](#-code-style)
- [Commit Conventions](#-commit-conventions)
- [Testing](#-testing)
- [Submitting a Pull Request](#-submitting-a-pull-request)
- [Reporting Bugs & Security Issues](#-reporting-bugs--security-issues)
- [Requesting Features](#-requesting-features)

---

## The One Rule That Matters Most

> **Every change must leave the repository in a runnable, tested state.**

Concretely:

- `pytest` must pass after your change.
- If you touch `nexora.App`'s public surface, the examples in `examples/` must still run (`python examples/basic_app.py`, etc.).
- Do not implement "half" of a feature module and leave the other half faked or hard-coded. If a module isn't finished, it stays registered as a `PlannedPlugin` (see `nexora/plugins/registry.py`) with an honest, descriptive `NotImplementedError` — never a silent no-op and never fabricated output.

---

## 🚀 Getting Started

### Prerequisites

- **Python** ≥ 3.10
- **pip** with support for editable installs
- **Git**

### Setup

```bash
# Clone the repository
git clone https://github.com/TejaPriyan/Nexora.git
cd Nexora

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify everything works
pytest
```

### Optional Dependencies

Some modules require optional extras. Install only what you need:

```bash
# For vision module development
pip install -e ".[vision]"

# For all optional dependencies
pip install -e ".[all]"
```

---

## 📁 Project Structure

```
Nexora/
├── src/
│   └── nexora/
│       ├── __init__.py           # Package entry point
│       ├── app.py                # Main App class
│       ├── plugins/
│       │   ├── base.py           # Plugin & PlannedPlugin base classes
│       │   └── registry.py       # Feature → Plugin class mapping
│       ├── security/
│       │   └── permissions.py    # PermissionManager for sensitive ops
│       ├── ghost/                # Ghost subsystem module
│       ├── vision/               # Vision subsystem module
│       ├── world/                # World subsystem module
│       ├── memory/               # Memory subsystem module
│       └── agentbox/             # AgentBox subsystem module
├── tests/                        # Test suite (mirrors src/ structure)
├── examples/                     # Runnable example scripts
├── docs/
│   ├── ROADMAP.md                # Feature milestones & priorities
│   └── ARCHITECTURE.md           # System design documentation
├── pyproject.toml                # Build config & dependencies
├── CHANGELOG.md                  # Version history
├── SECURITY.md                   # Security policy
└── LICENSE                       # MIT License
```

---

## 🧩 Adding a New Feature Module

Modules land **one at a time**, following `docs/ROADMAP.md`. To pick up the next milestone:

1. **Read** that milestone's section in `docs/ROADMAP.md`.
2. **Implement** the module under `src/nexora/<module_name>/`, as a real `nexora.plugins.Plugin` subclass (not `PlannedPlugin`).
3. **Update** `src/nexora/plugins/registry.py` to point that feature name at your new class instead of the `_planned(...)` placeholder.
4. **Add tests** under `tests/` covering the new module's public API.
5. **Update** the feature-status table in `README.md` and the corresponding section of `docs/ARCHITECTURE.md`.
6. **Dependencies**: If the module needs new third-party packages, add them as an optional extra in `pyproject.toml` (`[project.optional-dependencies]`) — the base install must stay dependency-free.
7. **Security**: Any privacy-sensitive capability (screen access, filesystem access beyond the project sandbox, network access, etc.) must be gated behind `nexora.security.PermissionManager.require(...)`.

### Module Checklist:
- [ ] Implements `Plugin` interface (not `PlannedPlugin`)
- [ ] Registered in `registry.py`
- [ ] Has comprehensive tests in `tests/`
- [ ] Optional dependencies in `pyproject.toml` extras
- [ ] Sensitive operations gated by `PermissionManager`
- [ ] README feature table updated
- [ ] `docs/ARCHITECTURE.md` updated
- [ ] Examples in `examples/` still run

---

## 🎨 Code Style

### General Principles
- **Type hints** on all public functions and methods.
- Prefer **explicit, small, well-named functions** over clever one-liners.
- New public behavior needs a test; bug fixes need a regression test.
- **Docstrings**: All public classes and functions must have Google-style docstrings.

### Formatting
- Line length: **88 characters** (Black default).
- Use **Black** for formatting and **Ruff** for linting:
  ```bash
  black src/ tests/
  ruff check src/ tests/
  ```

### Naming Conventions
| Element | Convention | Example |
|:---|:---|:---|
| Modules | `snake_case` | `vision_engine.py` |
| Classes | `PascalCase` | `VisionProcessor` |
| Functions | `snake_case` | `process_image()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Private | `_leading_underscore` | `_internal_state` |

---

## 📝 Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

### Types:

| Type | Description |
|:---|:---|
| `feat` | New feature or module |
| `fix` | Bug fix |
| `docs` | Documentation changes only |
| `style` | Code formatting (no logic change) |
| `refactor` | Code restructuring (no feature/fix) |
| `test` | Adding or fixing tests |
| `chore` | Build, CI, dependency updates |
| `perf` | Performance improvements |
| `security` | Security-related changes |

### Examples:
```bash
git commit -m "feat(vision): implement real-time image classification pipeline"
git commit -m "fix(memory): prevent infinite recursion in cache eviction"
git commit -m "test(ghost): add edge-case tests for message routing"
git commit -m "chore(deps): upgrade torch to 2.3.0 in vision extras"
```

---

## 🧪 Testing

### Running Tests

```bash
# Run the full suite
pytest

# Run with coverage report
pytest --cov=nexora --cov-report=term-missing

# Run tests for a specific module
pytest tests/test_vision.py

# Run a specific test
pytest tests/test_vision.py::test_image_classification -v
```

### Writing Tests

- Place tests in `tests/`, mirroring the `src/nexora/` structure.
- Use **pytest fixtures** for shared setup/teardown.
- Test both **happy paths** and **error cases**.
- For modules with optional dependencies, use `pytest.importorskip()`.

### Test Requirements:
- Every new public function/method needs at least one test.
- Every bug fix needs a regression test that fails without the fix.
- Tests must not require network access, API keys, or external services.

---

## 📬 Submitting a Pull Request

1. **Create** a branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make** your changes following the guidelines above.

3. **Test** thoroughly:
   ```bash
   pytest
   black --check src/ tests/
   ruff check src/ tests/
   ```

4. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request** against `main`.

### PR Description Template:
```markdown
## What does this PR do?
Brief description of the change.

## Motivation
Why is this needed? Link to ROADMAP milestone if applicable.

## How to test
Steps to verify the change manually.

## Checklist
- [ ] `pytest` passes
- [ ] `black` and `ruff` pass
- [ ] Type hints added to public API
- [ ] Docstrings added/updated
- [ ] Tests added for new behavior
- [ ] README/docs updated if needed
- [ ] Optional deps added to `pyproject.toml` extras (not base)
```

---

## 🐛 Reporting Bugs & Security Issues

### Bugs
[Open an issue](https://github.com/TejaPriyan/Nexora/issues/new) with:

- **Title**: Brief, descriptive summary
- **Environment**: Python version, OS, installed extras
- **Steps to reproduce**: Minimal code snippet or command
- **Expected vs. actual behavior**
- **Full traceback** (if applicable)

### Security Issues
⚠️ **Do NOT file security issues publicly.** See [SECURITY.md](SECURITY.md) for the responsible disclosure process.

---

## 💡 Requesting Features

[Open a feature request issue](https://github.com/TejaPriyan/Nexora/issues/new) with:

- Clear description of the proposed feature
- Which subsystem it relates to (ghost, vision, world, memory, agentbox)
- Whether it aligns with the current `docs/ROADMAP.md`
- Any reference implementations or papers

---

## 🙏 Thank You!

Every contribution — whether a single test, a documentation fix, or a complete module — helps make NEXORA better. **You are appreciated!**
