# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] -- Complete NEXORA Platform Release

The complete NEXORA runtime platform is now fully delivered across all 10 milestones.
All feature modules operate with zero direct cross-module imports, collaborating
exclusively through the shared `EventBus` and `State`.

### Added

- **Milestone 1 -- GhostUI (`nexora.ghost`)**: Automatic terminal dashboards via `rich`. Real-time task progress, status glyphs, error panels, metric counters, structured tables, and end-of-run summaries.
- **Milestone 2 -- CodeWorld (`nexora.world`)**: 2D entity visualization system via `pygame`. Spatial entity graph, relationships, properties, and EventBus bridges.
- **Milestone 3 -- MoodUI (`nexora.adaptive`)**: Interaction-aware adaptive interface system deriving states (`NORMAL`, `FAST`, `DIFFICULTY_HIGH`, `INACTIVE`, `ERROR_HEAVY`) purely from telemetry without emotion-detection claims. Gated by `PermissionManager`.
- **Milestone 4 -- Recall (`nexora.memory`)**: Persistent, structured application memory on SQLite `LocalStore`. Local semantic and keyword search, local Q&A without cloud AI APIs, and automatic secret redaction.
- **Milestone 5 -- TimeLoop (`nexora.timeline`)**: "Git for runtime application state". Checkpoints, snapshots, structural diffs, state restoration, backward/forward rewind, and secret scrubbing with custom exclusion lists.
- **Milestone 6 -- Shadow (`nexora.shadow`)**: Live observational execution model with nanosecond timing, function tracing (`@shadow.trace`), block spans, error capture with tracebacks, and dynamic dependency mapping. Zero synthetic or faked numbers.
- **Milestone 7 -- ScreenMind (`nexora.vision`)**: Explicitly-permissioned visual screen understanding: screenshot capture, template finding, text OCR locating, and color search. Strictly local-first, zero telemetry, and gated by `PermissionManager`. Click/type explicitly out of scope.
- **Milestone 8 -- WorldForge (`nexora.worldforge`)**: Procedural interactive world generation from Python structures: terrain maps, buildings, road networks, character rosters, and social bonds. Deterministic across runs given the same seed.
- **Milestone 9 -- AgentBox (`nexora.agentbox`)**: Sandboxed execution boundary for autonomous agents: tool allowlists, permission enforcement, step limits, tool call quotas, timeouts, dangerous action confirmation handlers, and full audit logs.
- **Milestone 10 -- Module Interoperability**: Decoupled event contracts across all modules: GhostUI renders TimeLoop checkpoints, Shadow alerts feed MoodUI friction detection, WorldForge populates CodeWorld spatial models, and verified architectural AST purity (zero cross-module imports).

---

## [0.1.0] -- Initial core release

### Added

- `nexora.events`: `EventBus` and `Event` -- the central pub/sub system
  every other subsystem is built on.
- `nexora.state`: `State`, an observable key/value container that emits
  `state.changed` / `state.deleted` events.
- `nexora.config`: `Config`, loading from `nexora.toml`, `NEXORA_*` env
  vars, and explicit overrides, with privacy-affecting defaults off.
- `nexora.security`: `PermissionManager` (explicit, audited, per-scope
  grants) and `SecretRedactor` (best-effort secret-key redaction).
- `nexora.storage`: `LocalStore`, a SQLite-backed, offline-only key/value
  store.
- `nexora.plugins`: `Plugin` / `PlannedPlugin` base classes and a feature
  registry mapping every planned module name to an honest placeholder.
- `nexora.runtime`: `Runtime`, wiring the above together per `App`
  instance.
- `nexora.App`: the top-level entry point, with `@app.task` registration,
  automatic `task.started` / `task.completed` / `task.failed` events, and
  `app.run()`.
- `nexora` CLI: `version`, `doctor`, `init`.
- Reserved packages (`nexora.ghost`, `nexora.world`, `nexora.adaptive`,
  `nexora.memory`, `nexora.timeline`, `nexora.vision`, `nexora.shadow`,
  `nexora.worldforge`, `nexora.agentbox`), each documented but not yet
  implemented -- see `docs/ROADMAP.md`.
- Full test suite (34 tests) covering every subsystem above.
- `examples/` demonstrating core usage end to end.
