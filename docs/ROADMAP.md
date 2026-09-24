# NEXORA Roadmap

NEXORA is built incrementally. Every milestone below must leave the
repository in a runnable, tested state before the next one starts -- no
milestone fakes a later one's functionality.

## Milestone 0 -- Core foundation (this release, v0.1.0) ✅

- [x] Event system (`nexora.events`)
- [x] State system (`nexora.state`)
- [x] Configuration (`nexora.config`)
- [x] Security / privacy layer (`nexora.security`)
- [x] Local storage primitive (`nexora.storage`)
- [x] Plugin architecture + feature registry (`nexora.plugins`)
- [x] `App` with task registration/execution (`nexora.app`)
- [x] CLI (`nexora version`, `nexora doctor`, `nexora init`)
- [x] Test suite covering every subsystem above
- [x] Reserved package + design docstring for every planned module

## Milestone 1 -- GhostUI ✅

Automatically render interfaces (tasks, progress, status, logs, errors,
metrics, tables) purely from `App`/`EventBus` activity. Optional
dependency: `rich`. Must not require the developer to hand-build a UI, and
must remain fully optional -- an app with no `ghost` feature must behave
identically to before.

- [x] `GhostPlugin` (real `Plugin` subclass, replaces `PlannedPlugin`)
- [x] Subscribes to task, progress, status, log, error, metric, table,
      and state events on the shared `EventBus`
- [x] Live task lifecycle rendering (started/completed/failed with timing)
- [x] Progress bar rendering with percentages, units, descriptions
- [x] Timestamped, color-coded structured log rendering
- [x] Error panels with tracebacks
- [x] Metric tracking (count, min, max, latest) and live display
- [x] Rich table rendering from event payloads
- [x] End-of-run summary dashboard (tasks table, metrics table, run banner)
- [x] Helper methods (`ghost.log()`, `.progress()`, `.metric()`, `.table()`, `.status()`)
- [x] Platform-aware glyph encoding (Windows cp1252 / UTF-8 consoles)
- [x] `quiet` mode to suppress all rendering while still tracking state
- [x] Fully optional -- zero impact when `ghost` not in `features`
- [x] Test suite (`tests/test_ghost.py`)
- [x] Example (`examples/ghost_ui_demo.py`)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md` feature-status table

## Milestone 2 -- CodeWorld ✅

2D visualization of application execution and state: entities,
properties, relationships, movement, simple rendering, inspection. 3D
rendering and full simulation are out of scope for this milestone.

- [x] `WorldPlugin` (real `Plugin` subclass, replaces `PlannedPlugin`)
- [x] `Entity` data model (ID, kind, position, colour, shape, label,
      custom properties, named relationships)
- [x] `World` container (thread-safe, add/remove/move/query entities)
- [x] Spatial queries: `entities_near()`, `entities_in_rect()`,
      `entities_by_kind()`, `entity_ids()`
- [x] All mutations emit events on shared `EventBus` via `_on_change` bridge
- [x] Auto-creates task entities from `task.started`/`completed`/`failed`
- [x] External world commands via events (`world.create`, `world.move`,
      `world.relate`, `world.remove`, `world.set_prop`)
- [x] `Renderer` (pygame-based 2D window): grid, entity shapes, relationship
      lines, labels, camera pan/zoom, entity selection/inspection
- [x] Model works without pygame; renderer is fully optional
- [x] Helper methods (`world.create()`, `.move()`, `.relate()`,
      `.set_prop()`, `.remove()`, `.get()`, `.entities()`, `.snapshot()`)
- [x] `app.world` convenience property
- [x] Fully optional -- zero impact when `world` not in `features`
- [x] Coexists with GhostUI (both subscribe to task events independently)
- [x] Test suite (`tests/test_world.py`)
- [x] Example (`examples/codeworld_demo.py`)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md` feature-status table

## Milestone 3 -- MoodUI (adaptive interfaces) ✅

Interaction-aware adaptive UI states (`NORMAL`, `FAST`, `DIFFICULTY_HIGH`,
`INACTIVE`, `ERROR_HEAVY`) derived from observable signals only (repeated
actions, failed actions, navigation loops, inactivity, help requests).
Explicitly does not claim to detect human emotion. Opt-in, no hidden
monitoring, built on `nexora.security.PermissionManager`.

- [x] `AdaptivePlugin` and `MoodUI` alias (real `Plugin` subclass, replaces `PlannedPlugin`)
- [x] Interaction states (`NORMAL`, `FAST`, `DIFFICULTY_HIGH`, `INACTIVE`, `ERROR_HEAVY`)
- [x] `AdaptiveEngine`: rule-based, deterministic, thread-safe state detection
- [x] Fast cadence detection for rapid successful actions
- [x] Error-heavy detection for consecutive or high-frequency task/error failures
- [x] Difficulty detection via repeated actions, navigation loops, and help requests
- [x] Inactivity timeout detection with configurable threshold
- [x] Recovery back to `NORMAL` state upon resumption of normal successful interactions
- [x] Privacy gate: explicit opt-in required via `PermissionManager` (scope `adaptive.observe`)
- [x] Zero observation or telemetry recording without explicit permission grant
- [x] Emits `adaptive.state_changed` event on shared `EventBus`
- [x] `app.adaptive` and `app.mood` convenience properties
- [x] Zero external dependencies (`requires_extra=None`, Python stdlib only)
- [x] Coexists with GhostUI and CodeWorld without interference
- [x] Test suite (`tests/test_adaptive.py`) with 100% state coverage and permission tests
- [x] Example (`examples/mood_ui_demo.py`)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md` feature-status table

## Milestone 4 -- Recall (memory) ✅

Persistent, structured application memory (`remember`, `search`, `ask`,
`forget`, `timeline`) built on `nexora.storage.LocalStore`. No requirement
on a paid AI API for the base functionality; optional embeddings/vector
search behind an extra. Sensitive information is never auto-uploaded.

- [x] `MemoryPlugin` and `Recall` alias (real `Plugin` subclass, replaces `PlannedPlugin`)
- [x] `MemoryItem` data model (id, content, value, tags, metadata, timestamp)
- [x] `MemoryStore` backed by `LocalStore` (local SQLite persistence)
- [x] Automatic secret redaction for values, metadata, and content via `SecretRedactor`
- [x] `remember()`, `search()`, `ask()`, `forget()`, `timeline()`, `clear()` methods
- [x] Pure local execution with zero network calls and no paid AI API required
- [x] Emits `memory.remembered`, `memory.forgotten`, `memory.cleared` events
- [x] External command event handlers (`memory.remember`, `memory.forget`, `memory.clear`)
- [x] `app.memory` and `app.recall` convenience properties
- [x] Coexists with GhostUI, CodeWorld, and MoodUI without interference
- [x] Test suite (`tests/test_memory.py`) verifying CRUD, search, ask, redaction, and no network calls
- [x] Example (`examples/recall_demo.py`)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md` feature-status table

## Milestone 5 -- TimeLoop (timeline / rewind) ✅

"Git for runtime application state": `checkpoint`, `snapshot`, `restore`,
`rewind`, `diff`, `history` for tracked objects. Every tracked snapshot is
run through `nexora.security.SecretRedactor`, plus an explicit
`.ignore("password", "api_key", ...)` exclusion list. Does not claim
perfect secret detection.

- [x] `TimelinePlugin` and `TimeLoop` alias (real `Plugin` subclass, replaces `PlannedPlugin`)
- [x] `Snapshot` and `DiffResult` data models
- [x] `TimeLoopEngine` supporting checkpoints, restore, rewind, forward, diff
- [x] Automatic secret redaction for all snapshots via `SecretRedactor`
- [x] Custom exclusion list support via `.ignore("password", "api_key", ...)`
- [x] Structural diff calculation (added, removed, changed keys)
- [x] State synchronization with `app.state` on restore/rewind
- [x] Emits `timeline.checkpoint`, `timeline.restored`, `timeline.rewound` events
- [x] `app.timeline` and `app.timeloop` convenience properties
- [x] Coexists with GhostUI, CodeWorld, MoodUI, and Recall without interference
- [x] Test suite (`tests/test_timeline.py`) verifying checkpoints, secret redaction, custom ignore, diff, rewind
- [x] Example (`examples/timeloop_demo.py`)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md` feature-status table

## Milestone 6 -- Shadow (observability) ✅

A live observational model of a running application: functions, events,
state, execution timing, errors, dependencies. Targets reliable
observability first, not an "AI debugger" -- zero synthetic numbers or placeholder data.

- [x] `ShadowPlugin` and `Shadow` alias (real `Plugin` subclass, replaces `PlannedPlugin`)
- [x] `FunctionProfile`, `ObservedEvent`, `ObservedError`, `DependencyLink`, `ObservabilitySnapshot` data models
- [x] `ShadowEngine` measuring genuine execution durations with `perf_counter`
- [x] `@shadow.trace` decorator for function profiling and exception capture
- [x] `shadow.span("name")` context manager for block timing
- [x] Dynamic dependency tree mapping (`shadow.dependencies()`)
- [x] Event bus flow monitoring (`shadow.event_stats()`)
- [x] Error and exception logging with full tracebacks (`shadow.errors()`)
- [x] Auto-observes `task.started`, `task.completed`, `task.failed` and emits `shadow.alert`
- [x] `app.shadow` convenience property
- [x] Coexists with GhostUI, CodeWorld, MoodUI, Recall, and TimeLoop
- [x] Test suite (`tests/test_shadow.py`) verifying genuine timing, error capture, dependencies
- [x] Example (`examples/shadow_demo.py`)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md` feature-status table

## Milestone 7 -- ScreenMind (vision) ✅

Explicitly-permissioned screen perception (`screenshot`, `find`,
`find_text`, `locate`), gated end-to-end behind
`nexora.security.PermissionManager`. Defaults: no recording, no cloud
upload, no telemetry, no hidden capture. Local processing preferred. Click and type strictly out of scope.

- [x] `VisionPlugin` and `ScreenMind` alias (real `Plugin` subclass, replaces `PlannedPlugin`)
- [x] `BBox`, `MatchResult`, `ScreenImage` data models
- [x] `VisionEngine` supporting screenshots, template matching, text search, and color locating
- [x] Privacy gate: requires `vision.screenshot`, `vision.find`, `vision.ocr`, `vision.locate` scopes
- [x] `PermissionDenied` raised automatically when unpermissioned actions are attempted
- [x] Local-first processing with zero network calls and zero telemetry
- [x] Mock capture support for deterministic CI testing without real displays
- [x] Event emission: `vision.screenshot.captured` and `vision.pattern.found`
- [x] `app.vision` and `app.screenmind` convenience properties
- [x] Click and type strictly not implemented to prevent unauthorized agent takeovers
- [x] Test suite (`tests/test_vision.py`) verifying permission gating, matching, OCR hooks, and privacy
- [x] Example (`examples/vision_demo.py`)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md` feature-status table

## Milestone 8 -- WorldForge ✅

Procedural interactive worlds generated from Python structures: entities,
maps, buildings, roads, characters, relationships, basic procedural
generation. Shares the `world` pip extra with CodeWorld -- reuses its
entity/rendering primitives without photorealistic 3D bloat.

- [x] `WorldForgePlugin` and `WorldForge` alias (real `Plugin` subclass, replaces `PlannedPlugin`)
- [x] `Building`, `Road`, `Character`, `WorldMap` data models
- [x] `ProceduralGenerator` providing fully deterministic seeded generation
- [x] `WorldForgeEngine` managing manual and procedurally generated assets
- [x] Automatic translation of buildings and characters to CodeWorld `Entity` objects
- [x] Social relationships and network generation (`char.relate(type, target)`)
- [x] Event emission: `worldforge.generated`, `worldforge.building.created`, etc.
- [x] `app.worldforge` convenience property
- [x] Full world snapshot export (`app.worldforge.export_world()`)
- [x] Test suite (`tests/test_worldforge.py`) verifying structures, relationships, and deterministic seeds
- [x] Example (`examples/worldforge_demo.py`)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md` feature-status table

## Milestone 9 -- AgentBox ✅

Sandboxed, permissioned execution for autonomous agents: permission
policies, tool allowlists, execution limits, timeouts, logs, an audit
trail, sandbox abstraction, and confirmation prompts for dangerous
actions. Limitations documented explicitly in `docs/ARCHITECTURE.md`.

- [x] `AgentBoxPlugin` and `AgentBox` alias (real `Plugin` subclass, replaces `PlannedPlugin`)
- [x] `ToolDefinition`, `ToolCallRecord`, `AgentExecutionLimits`, `AgentPolicy`, `AgentResult` models
- [x] `Sandbox` execution boundary with allowlists and limit enforcement
- [x] Permission gating via `PermissionManager` integration
- [x] Confirmation prompt handler for dangerous actions (`requires_confirmation`)
- [x] Execution quotas: step limits, tool call limits, timeouts
- [x] Complete, immutable tool invocation audit trail (`audit_trail()`)
- [x] Autonomous agent execution runner (`app.agentbox.run_agent(...)`)
- [x] Event emission: `agentbox.tool.executed`, `agentbox.tool.blocked`, `agentbox.agent.completed`, etc.
- [x] `app.agentbox` convenience property
- [x] Explicit documentation of sandbox security boundaries and limitations in `docs/ARCHITECTURE.md`
- [x] Test suite (`tests/test_agentbox.py`) verifying allowlists, permissions, limits, and audit trails
- [x] Example (`examples/agentbox_demo.py`)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md` feature-status table

## Milestone 10 -- Module interoperability ✅

Integration and event-based decoupling across all 9 modules: zero direct
cross-module imports, event contracts, unified execution, and v1.0.0 release.

- [x] Zero direct cross-module imports: all modules interact strictly via `EventBus` and `State`
- [x] GhostUI renders TimeLoop checkpoint/restore/rewind events live
- [x] Shadow observability alerts feed into MoodUI friction and difficulty detection
- [x] WorldForge drives CodeWorld 2D entity creation and relationships purely via events
- [x] Recall memory, TimeLoop snapshots, and AgentBox collaborate seamlessly through App context
- [x] Module Interoperability event contract matrix documented in `docs/ARCHITECTURE.md`
- [x] Automated AST purity test ensuring zero direct sibling imports (`tests/test_interop.py`)
- [x] Comprehensive multi-module integration test suite (`tests/test_interop.py`)
- [x] Bumped version to 1.0.0 in `pyproject.toml` and `src/nexora/_version.py`
- [x] Added complete v1.0.0 release summary to `CHANGELOG.md`
- [x] All 10 milestones finished, verified, and checked off

---

Each milestone, when it lands, gets: a real implementation (no
pseudocode), its own tests, an updated `docs/ARCHITECTURE.md` section, an
updated feature-status table in `README.md`, and its registry entry in
`nexora.plugins.registry` switched from `PlannedPlugin` to the real
`Plugin` subclass.
