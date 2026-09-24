# NEXORA Architecture

NEXORA is built in strict layers, bottom-up, per the project's core
development rule: **build a real foundation first, then add modules one
at a time, always leaving the repository runnable.**

```
NEXORA CORE
   |
   v
Plugin architecture   (nexora.plugins)
   |
   v
Event system          (nexora.events)
   |
   v
State system           (nexora.state)
   |
   v
Configuration          (nexora.config)
   |
   v
Security / privacy layer   (nexora.security)
   |
   v
CLI                    (nexora.cli)
   |
   v
Feature modules, one milestone at a time:
   ✅ ghost (GhostUI, Milestone 1)
   ✅ world (CodeWorld, Milestone 2)
   ✅ adaptive (MoodUI, Milestone 3)
   ✅ memory (Recall, Milestone 4)
   ✅ timeline (TimeLoop, Milestone 5)
   🚧 vision, shadow, worldforge, agentbox
```

This document describes the layers that exist **today** (Milestone 5). For what
is planned but not yet built, see [ROADMAP.md](ROADMAP.md).

## `nexora.events` -- the integration point

Every other subsystem communicates through `EventBus`. Events carry a
`type`, `source`, `payload` dict, `metadata` dict, a unique `id`, and a UTC
`timestamp` (see `Event` in `nexora/events/bus.py`). Handlers can subscribe
to an exact type, a glob pattern (`"task.*"`), or everything (`"*"`), and
run synchronously in subscription order on the emitting thread -- this
keeps ordering predictable and makes the bus trivial to unit test.

`EventBus` keeps a bounded in-memory `history()` (default: last 1000
events) so a UI (GhostUI) or a debugger (later: Shadow) can inspect
recent activity without needing to have subscribed in advance.

## `nexora.state` -- observable state

`State` is a small, thread-safe key/value container. Every `set()` /
`delete()` that changes a value emits `state.changed` / `state.deleted` on
whatever `EventBus` it was constructed with, so nothing needs to poll for
changes. `App.state` is a `State` wired to the app's own bus.

## `nexora.plugins` -- the extension point

A NEXORA "feature" (the strings you pass to `App(features=[...])`, like
`"ghost"` or `"memory"`) resolves through `nexora.plugins.registry` to a
`Plugin` subclass. `Plugin` defines three lifecycle hooks:
`on_register()`, `on_start()`, `on_stop()`.

As of Milestone 1, `"ghost"` resolves to the real `GhostPlugin` subclass.
All other features still resolve to `PlannedPlugin`: they register cleanly
(so `App(features=["memory"])` doesn't crash and `app.runtime.plugins`
reflects what you asked for), but their `on_start()` raises a
`NotImplementedError` describing what the module will do and pointing at
the roadmap. This is a deliberate design choice: NEXORA would rather fail
loudly and honestly than silently no-op or fake a capability that isn't
built yet.

As each subsequent module milestone lands, its registry entry will start
pointing at a real `Plugin` subclass instead of `PlannedPlugin` --
callers do not need to change any code.

## `nexora.config` -- configuration

`Config` is intentionally boring: an optional `nexora.toml`
(`[nexora]` table) in the current directory, then `NEXORA_*` environment
variables, then explicit constructor overrides, in increasing order of
precedence. Privacy-affecting fields (`telemetry`, `cloud_sync`) default to
`False`.

## `nexora.security` -- privacy and secrets

Two independent pieces:

- `PermissionManager` -- an explicit, per-scope grant/revoke/require API
  with an audit trail. Nothing is granted by default. Future
  privacy-sensitive modules (ScreenMind, AgentBox) are expected to gate
  every sensitive action behind a `permissions.require("scope.action")`
  call.
- `SecretRedactor` -- a best-effort, denylist-based redactor for
  dict-shaped data, plus an explicit `.ignore(...)` list for
  caller-specified sensitive fields. It does not claim perfect detection.
  The (planned) TimeLoop module is expected to run every tracked snapshot
  through this before persisting or diffing it.

## `nexora.storage` -- local persistence

`LocalStore` is a namespaced key/value store on top of SQLite, stored
under `~/.nexora/<name>.sqlite3` by default. No network calls, no
telemetry. This is the shared persistence primitive the (planned)
Recall/Memory and TimeLoop/Timeline modules will build on.

## `nexora.runtime` -- wiring

`Runtime` is the object that actually owns an app's `EventBus`, `State`,
`PermissionManager`, `Config`, and the dict of registered `Plugin`
instances. `App` is a thin, ergonomic wrapper around `Runtime` plus a task
registry.

## `nexora.App` -- the top-level object

`App` adds one more concept on top of `Runtime`: **tasks**. `@app.task`
wraps a function so every call emits `task.started` / `task.completed` /
`task.failed` with timing, regardless of whether any UI module is
installed to *render* that activity. `app.run()` starts the runtime
(which starts every registered plugin -- this is where a planned feature's
`NotImplementedError` would surface), then runs every registered task
through the same wrapped path.

## `nexora.cli` -- developer experience

A small, stdlib-only (`argparse`) CLI: `nexora version`, `nexora doctor`
(reports which optional extras are installed and which features are still
planned), and `nexora init` (scaffolds a starter `app.py`).

## `nexora.ghost` -- automatic terminal interfaces (Milestone 1)

`GhostPlugin` (aliased as `GhostUI`) is the first feature module built on
top of the NEXORA core. It automatically renders rich terminal interfaces
purely by observing events already flowing on the shared `EventBus` --
the developer does not hand-build a UI. Optional dependency: `rich>=13.0`
(declared as `nexora[ghost]`).

Subscribed event families and what they render:

- **Tasks** (`task.started`, `task.completed`, `task.failed`): live
  lifecycle indicators with duration timing and failure alerts.
- **Progress** (`progress`, `progress.*`, `task.progress`): progress bars
  with completion percentages, rates, and units.
- **Status** (`status`, `status.*`): reactive status badges.
- **Logs** (`log`, `log.*`): timestamped, color-coded log entries with
  level badges (DEBUG, INFO, WARN, ERROR, CRITICAL).
- **Errors** (`error`, `error.*`): boxed panels showing error messages
  and formatted tracebacks.
- **Metrics** (`metric`, `metric.*`): live metric tracking (count, min,
  max, latest value) with unit display.
- **Tables** (`table`, `table.*`): formatted Rich data tables.
- **State** (`state.changed`): optional state-change inspection (off by
  default).

At shutdown (`on_stop()`), GhostUI generates an end-of-run dashboard:

1. **Tasks Summary Table** -- each task, its status badge, duration,
   and error details.
2. **Metrics Summary Table** -- tracked metrics, update counts, latest
   values, and min/max ranges.
3. **Run Summary Banner** -- total tasks, completed/failed counts, and
   wall-clock elapsed time.

GhostUI stays 100 % optional: apps without `features=["ghost"]` are
completely unaffected. The plugin uses platform-aware glyph encoding so
it works across Windows (cp1252), Linux, and macOS consoles.

Helper methods (`ghost.log()`, `ghost.progress()`, `ghost.metric()`,
`ghost.table()`, `ghost.status()`) let developers emit structured events
conveniently, but every one of them simply calls `app.bus.emit(...)` --
GhostUI never bypasses the shared bus.

## `nexora.world` -- 2D entity visualization (Milestone 2)

`WorldPlugin` (aliased as `CodeWorld`) is the second feature module, providing
a 2D spatial model of entities that represent application state.  The module
separates the **model** (`World` + `Entity`) from the **renderer** (pygame):

- `Entity` -- a positioned, typed object with a colour, shape, label, custom
  properties, and named relationships to other entities.
- `World` -- a thread-safe container of entities supporting spatial queries
  (`entities_near()`, `entities_in_rect()`, `entities_by_kind()`).
  Every mutation on `World` fires an event through a callback that
  `WorldPlugin` wires to `app.bus.emit()`.
- `Renderer` -- a pygame-based 2D window with grid, entity drawing,
  relationship lines, camera pan/zoom, hit-testing, and an inspector panel
  for selected entities.  Fully optional: `World` works without pygame.

Subscribed event families:

- **Tasks** (`task.started`, `task.completed`, `task.failed`): auto-creates
  entity representations of tasks with colour-coded status badges.
- **World commands** (`world.create`, `world.remove`, `world.move`,
  `world.relate`, `world.set_prop`): external code can drive the world
  entirely through the shared EventBus.

Emitted events (from World mutations):

- `world.entity.added`, `world.entity.removed`, `world.entity.moved`,
  `world.entity.property`, `world.entity.related`, `world.entity.unrelated`,
  `world.cleared`, `world.started`, `world.stopped`.

Convenience helpers (`world.create()`, `.move()`, `.relate()`, `.set_prop()`,
`.remove()`, `.entities()`, `.snapshot()`, `.get()`) mirror `World` methods
and ensure all mutations go through the EventBus.

CodeWorld stays 100% optional: apps without `features=["world"]` are
completely unaffected.  It coexists freely with GhostUI -- both plugins
subscribe to task events independently.

## `nexora.adaptive` -- MoodUI (Milestone 3)

Interaction-aware adaptive interface system (`AdaptivePlugin`, `MoodUI`) that
derives interface states purely from observable interaction telemetry:

- **States**: `NORMAL`, `FAST`, `DIFFICULTY_HIGH`, `INACTIVE`, `ERROR_HEAVY`.
- **Observable signals**:
  - Task lifecycle and errors (`task.started`, `task.completed`, `task.failed`, `error`).
  - Action cadence and repeated attempts (`action`, `interaction`).
  - Navigation patterns and route loops (`navigation`, `nav`).
  - Help and documentation requests (`help`, `help.requested`).
  - Inactivity periods exceeding configurable timeouts (`adaptive.inactivity_check`).

### Privacy and Permission Gate

MoodUI **explicitly does not claim to detect human emotion**; it models interaction
friction, cadence, and failure rates from objective telemetry.

Privacy is enforced through `nexora.security.PermissionManager`:
- Requires explicit opt-in under permission scope `"adaptive.observe"`.
- Zero observation occurs without this permission: events arriving before opt-in
  are ignored, and programmatic tracking methods raise `PermissionDenied`.
- Opt-in and opt-out can be changed dynamically (`app.adaptive.opt_in()`,
  `app.adaptive.opt_out()`).

### Emitted Events

Whenever the interaction state changes, MoodUI emits:
- `adaptive.state_changed` with payload containing `previous_state`,
  `current_state`, `reason`, `timestamp`, and `metadata`.

MoodUI is zero-dependency (Python stdlib only, `requires_extra=None`). It coexists
cleanly with `ghost` and `world`, enabling self-adjusting interfaces without
direct coupling.

## `nexora.memory` -- Recall (Milestone 4)

Persistent, structured application memory system (`MemoryPlugin`, `Recall`)
built on top of `nexora.storage.LocalStore`:

- **Core Capabilities**:
  - `remember(key_or_content, value=None, tags=None, metadata=None)`: stores structured memory items.
  - `search(query, tags=None, limit=10)`: keyword and tag search with relevance ranking.
  - `ask(question)`: local deterministic retrieval answering without external AI APIs.
  - `forget(key)`: removes specific memory entries.
  - `timeline(limit=None, reverse=False)`: chronological inspection of memories.

### Privacy & Secret Redaction

- **Zero Cloud Upload**: Everything is stored in local SQLite (`~/.nexora/nexora_memory.sqlite3`).
- **Automatic Redaction**: Before persistence, every memory value and metadata dict is scrubbed
  through `nexora.security.SecretRedactor` to prevent accidental credential leakage.

### Emitted Events

- `memory.remembered` (`id`, `tags`, `timestamp`)
- `memory.forgotten` (`id`)
- `memory.cleared`

Supports external event-driven commands via `memory.remember`, `memory.forget`,
and `memory.clear`.

## `nexora.timeline` -- TimeLoop (Milestone 5)

Runtime application state versioning, diff, and rewind system (`TimelinePlugin`,
`TimeLoop`):

- **Capabilities**:
  - `checkpoint(label, data=None, metadata=None)`: saves a point-in-time state snapshot (defaults to `app.state`).
  - `snapshot()`: returns the active state checkpoint.
  - `restore(snapshot_id, apply_to_state=True)`: restores application state back to a past checkpoint.
  - `rewind(steps=1, apply_to_state=True)`: steps backward along the timeline.
  - `forward(steps=1, apply_to_state=True)`: steps forward along the timeline.
  - `diff(source, target)`: returns a structural diff (`added`, `removed`, `changed`).
  - `history()`: returns chronological checkpoints.
  - `ignore(*keys)`: adds custom keys to the secret exclusion list.

### Privacy & Secret Redaction

- Every state snapshot is automatically scrubbed by `nexora.security.SecretRedactor`
  before storage or diff computation.
- Explicit support for `.ignore("password", "api_key", ...)` prevents sensitive tokens
  from being captured in snapshots. Does not claim perfect secret detection.

### Emitted Events

- `timeline.checkpoint` (`id`, `label`, `timestamp`, `keys_count`)
- `timeline.restored` (`id`, `label`, `timestamp`)
- `timeline.rewound` (`id`, `label`, `steps`)
- `timeline.forwarded` (`id`, `label`, `steps`)

## `nexora.shadow` -- Shadow (Milestone 6)

Live observational telemetry and execution profiling module (`ShadowPlugin`, `Shadow`):

- **Capabilities**:
  - `@shadow.trace`: Function decorator measuring genuine execution durations, call frequencies, and capturing unhandled exceptions.
  - `shadow.span("name")`: Context manager to time blocks of code with real-time nanosecond-resolution measurements.
  - `shadow.function_stats(name=None)`: Returns min/max/average execution times, call counts, and failure counts for observed functions.
  - `shadow.event_stats()`: Maps frequency and sources of events flowing through the `EventBus`.
  - `shadow.dependencies()`: Captures calling relationships and dependency invocation trees between components.
  - `shadow.errors()`: Point-in-time log of captured exceptions with full stack traces.
  - `shadow.snapshot()`: Produces an `ObservabilitySnapshot` capturing the complete runtime profile.

### Zero Synthetic Data

Shadow is designed strictly for reliable application observability:
- Timing is measured using high-precision hardware counters (`time.perf_counter()`).
- No placeholder, synthetic, or AI-generated debugger analysis is used.
- Subscribes dynamically to `task.started`, `task.completed`, and `task.failed` events to record actual task execution metrics automatically.

### Emitted Events

- `shadow.alert`: Emitted when an error is caught or a monitored task fails (`error`, `source`).

## `nexora.vision` -- ScreenMind (Milestone 7)

Explicitly-permissioned visual perception and screen understanding module (`VisionPlugin`, `ScreenMind`):

- **Capabilities**:
  - `screenshot(region=None)`: Captures full screen or region as `ScreenImage`.
  - `find(template, image=None, threshold=0.8)`: Locates visual templates with coordinate bounding boxes and confidence score.
  - `find_text(text, image=None, case_sensitive=False)`: Locates text elements visually across the screen.
  - `locate(color, image=None, tolerance=15)`: Identifies regions containing target colors or UI indicators.

### Privacy-First Non-Negotiables

- **Gated by PermissionManager**: Zero visual operations execute without explicit consent.
  - `screenshot()` requires `"vision.screenshot"`.
  - `find()` requires `"vision.find"`.
  - `find_text()` requires `"vision.ocr"`.
  - `locate()` requires `"vision.locate"`.
  - Unpermissioned access raises `nexora.security.PermissionDenied`.
- **Zero Hidden Telemetry**: No background recording, no cloud upload, no telemetry.
- **Strictly No Click/Type**: Direct input simulation is out of scope to prevent unauthorized agent takeovers.

### Emitted Events

- `vision.screenshot.captured` (`width`, `height`, `timestamp`, `region`)
- `vision.pattern.found` (`bbox`, `confidence`, `label`)

## `nexora.worldforge` -- WorldForge (Milestone 8)

Interactive procedural world generation and environment management module (`WorldForgePlugin`, `WorldForge`):

- **Capabilities**:
  - `generate(seed=42, width=20, height=15, num_buildings=6, num_roads=4, num_characters=5)`: Deterministic procedural generation of terrain maps, building placements, connecting road networks, and populated character rosters.
  - `create_building(name, building_type, x, y, width=40, height=40, floors=1, **properties)`: Explicitly places structured building assets.
  - `create_road(name, start_pos, end_pos, road_type="paved", lanes=2, connected_nodes=None)`: Constructs connecting pathway networks between nodes.
  - `create_character(name, role, x=0, y=0, home_id=None, workplace_id=None, inventory=None)`: Creates interactive characters with homes and inventories.
  - `relate(char_a_id, rel_type, char_b_id)`: Generates social and organizational links between entities.
  - `export_world()`: Exports full serializable dictionary representation of the world.

### Deterministic Procedural Generation

- Uses seeded pseudo-random generation (`ProceduralGenerator(seed)`).
- Given the same seed, identically replicates terrain tiles, structure placement coordinates, road paths, character names, and relationships.
- Bridges seamlessly with `nexora.world.World` to render structures in 2D without photorealistic 3D bloat.

### Emitted Events

- `worldforge.generated` (`seed`, `buildings_count`, `roads_count`, `characters_count`)
- `worldforge.building.created` (`id`, `name`, `type`, `x`, `y`)
- `worldforge.road.created` (`id`, `name`, `start`, `end`)
- `worldforge.character.created` (`id`, `name`, `role`, `x`, `y`)
- `worldforge.character.related` (`source`, `relation`, `target`)

## `nexora.agentbox` -- AgentBox (Milestone 9)

Sandboxed execution and governance layer for autonomous agents (`AgentBoxPlugin`, `AgentBox`):

- **Capabilities**:
  - `register_tool(name, func, dangerous=False, permission_scope=None, allow_by_default=False)`: Registers controlled functions accessible to agents.
  - `allow_tool(name)` / `disallow_tool(name)`: Dynamically manages per-sandbox tool allowlists.
  - `create_sandbox(...)`: Creates isolated execution boundaries with custom policies and limits.
  - `set_confirmation_handler(handler)`: Connects human-in-the-loop confirmation prompts for dangerous operations.
  - `run_agent(agent_func, limits=None, allowed_tools=None)`: Runs agent control loops under strict quotas and timeouts.
  - `audit_trail()`: Complete immutable audit log of every tool execution attempt, status, and duration.

### Security Guarantees & Non-Negotiables

- **Default-Deny Access**: By default, an agent has zero access to tools or capabilities. Every tool must be explicitly registered and placed on the sandbox's allowlist.
- **Permission Verification**: Gated behind `nexora.security.PermissionManager` scopes. Even if a tool is allowlisted, lack of explicit permission denies execution.
- **Dangerous Action Interception**: Destructive or sensitive operations require interactive confirmation approval.
- **Resource Constraints**: Strict limits on max steps, max tool calls, and per-tool execution timeouts.

### Limitations of the Sandbox (Explicit Disclosure)

> [!WARNING]
> **AgentBox is NOT an impenetrable hypervisor or multi-tenant OS jail.**
> 
> - **In-Process Boundary**: AgentBox operates at the Python runtime layer. It governs agent function dispatch, tool calling, and resource accounting.
> - **C-Extension & Memory Exploits**: It does not defend against arbitrary byte-code injections, C-extension exploits, or kernel-level escapes if untrusted native code is executed.
> - **Process DOS**: While execution timeouts prevent long-running threads from hanging the agent loop, unbounded memory allocations within arbitrary third-party libraries cannot be strictly preempted without operating-system-level cgroups / containers.
> - **Intended Use**: AgentBox is built for orchestrating autonomous agents with defense-in-depth safety, human oversight, tool governance, and audit trails -- not running adversarial unverified binaries.

### Emitted Events

- `agentbox.agent.started` (`agent_id`)
- `agentbox.agent.completed` (`agent_id`, `success`, `steps`)
- `agentbox.tool.executed` (`tool`, `status`)
- `agentbox.tool.blocked` (`tool`, `reason`)
- `agentbox.confirmation.denied` (`tool`, `reason`)

## Module Interoperability (Event Contracts)

In NEXORA v1.0, all 9 feature modules (`ghost`, `world`, `adaptive`, `memory`, `timeline`, `shadow`, `vision`, `worldforge`, `agentbox`) are fully implemented and operate with **zero direct cross-module imports**. All inter-module communication is decoupled through the shared `EventBus` and `State`.

### Inter-Module Event Contracts

| Contract / Event Family | Emitted By | Consumed By | Payload Contract | Description |
|---|---|---|---|---|
| `task.started`, `task.completed`, `task.failed` | `App` | `GhostUI`, `CodeWorld`, `MoodUI`, `Shadow` | `{"task": str, "duration_seconds": float, "error": Optional[str]}` | Central task lifecycle; drives GhostUI displays, CodeWorld visual nodes, MoodUI cadence, and Shadow timing. |
| `timeline.checkpoint`, `timeline.restored`, `timeline.rewound` | `TimeLoop` | `GhostUI`, `State` | `{"id": str, "label": str, "keys_count": int, "steps": int}` | Runtime state checkpoints and diff rewind; rendered live by GhostUI and synchronized into application state. |
| `shadow.alert` | `Shadow` | `MoodUI` | `{"error": str, "source": str}` | Genuine observability alerts from monitored executions; consumed by MoodUI as friction and difficulty signals. |
| `world.create`, `world.relate`, `world.move` | `WorldForge`, caller | `CodeWorld` | `{"entity_id": str, "kind": str, "x": float, "y": float, "label": str, ...}` | Unified 2D spatial visualization commands; WorldForge drives CodeWorld rendering entirely over the event bus. |
| `memory.remembered`, `memory.forgotten` | `Recall` | `GhostUI`, logging | `{"id": str, "tags": List[str], "timestamp": float}` | Structured memory audit events; track memory storage and eviction events across modules. |
| `vision.screenshot.captured`, `vision.pattern.found` | `ScreenMind` | External observers, Agents | `{"width": int, "height": int, "bbox": dict, "confidence": float}` | Perception events broadcast when permissioned captures and pattern matches succeed. |
| `agentbox.tool.executed`, `agentbox.tool.blocked`, `agentbox.confirmation.denied` | `AgentBox` | `GhostUI`, `Shadow` | `{"tool": str, "status": str, "reason": Optional[str]}` | Agent governance audit events; surface blocked operations and confirmation interventions in real time. |

### Architectural Purity Enforcement

- **AST Purity Guarantee**: Enforced by automated continuous testing in `tests/test_interop.py::test_zero_direct_cross_module_imports`.
- **Loose Coupling**: Any combination of modules can be loaded (e.g. `App(features=["ghost", "timeline"])` or `App(features=["shadow", "adaptive"])`) without missing dependency errors.
- **Pluggable Architecture**: Modules are discoverable and instantiable purely through `App(features=[...])`.
