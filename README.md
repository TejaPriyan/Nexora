# NEXORA

**One Python ecosystem. Many capabilities. Completely modular. Local-first. Privacy-first. Open-source.**

NEXORA is a modular Python runtime. The long-term vision is to give ordinary
Python applications new capabilities -- automatic interfaces, visual
application/world representations, adaptive interfaces, persistent
application memory, state history and rewind, screen/computer perception,
live application observation, interactive world generation, and controlled
AI-agent execution -- all built on one small, shared runtime.

This is **not** meant to become another chatbot wrapper, terminal UI
library, game engine, vector database wrapper, agent wrapper, or
automation library on its own. Each capability is a module; the modules
share one event system, one state model, one security/privacy layer, and
one CLI.

> **Status: v1.0.0 (Complete Platform Release).** All 10 milestones are fully implemented and verified:
> NEXORA Core, **GhostUI** (Milestone 1), **CodeWorld** (Milestone 2), **MoodUI** (Milestone 3),
> **Recall** (Milestone 4), **TimeLoop** (Milestone 5), **Shadow** (Milestone 6),
> **ScreenMind** (Milestone 7), **WorldForge** (Milestone 8), **AgentBox** (Milestone 9),
> and **Module Interoperability** (Milestone 10) -- see [What's implemented today](#whats-implemented-today)
> and [docs/ROADMAP.md](docs/ROADMAP.md). Every module communicates strictly through the shared EventBus and State with zero cross-module imports.

---

## Install

```bash
pip install nexora-py
```

The base install is dependency-free (Python stdlib only). Feature modules
pull in extras as needed, e.g.:

```bash
pip install nexora-py[ghost]    # rich (GhostUI automatic terminal interfaces)
pip install nexora-py[world]    # pygame (CodeWorld 2D entity visualization)
pip install nexora-py[vision]   # pillow + mss (ScreenMind screen perception)
pip install nexora-py[ai]       # numpy, for numerical operations
pip install nexora-py[all]      # everything above
```

*(Note: The package installs as `nexora-py`, and is imported in Python directly as `nexora`, e.g. `import nexora` or `from nexora import App`.)*

## Quickstart

```python
from nexora import App

app = App()

@app.task
def process_data():
    print("processing...")

app.run()
```

Every task call automatically emits `task.started` / `task.completed` /
`task.failed` events on the app's event bus, which anything else in the
process can subscribe to:

```python
@app.bus.on("task.completed")
def on_done(event):
    print(f"{event.payload['task']} took {event.payload['duration_seconds']:.3f}s")
```

See [`examples/`](examples/) for runnable demonstrations:
- **`showcase_all.py`**: **Master live showcase of all 10 milestones in action!**
- `ghost_ui_demo.py`: GhostUI automatic terminal UI dashboards, logs, and metrics
- `codeworld_demo.py`: CodeWorld 2D entity visualization and spatial topology
- `mood_ui_demo.py`: MoodUI interaction-aware adaptive interfaces and friction detection
- `recall_demo.py`: Recall persistent application memory with secret redaction
- `timeloop_demo.py`: TimeLoop runtime state checkpoints, rewind, and structural diff
- `shadow_demo.py`: Shadow live observability, high-resolution timing, and error tracking
- `vision_demo.py`: ScreenMind explicitly-permissioned screen perception
- `worldforge_demo.py`: WorldForge interactive procedural world generation
- `agentbox_demo.py`: AgentBox sandboxed autonomous agent execution
- `events_demo.py`: Using `EventBus` standalone
- `state_and_storage_demo.py`: Observable state + local persistence

## CLI

```bash
nexora version     # print the installed version
nexora doctor       # check which optional extras are installed
nexora init myapp   # scaffold a new NEXORA app
```

## What's implemented today

| Layer | Status | Module |
|---|---|---|
| Event system | ✅ implemented | `nexora.events` (`EventBus`, `Event`) |
| State | ✅ implemented | `nexora.state` (`State`) |
| Configuration | ✅ implemented | `nexora.config` (`Config`) |
| Security / privacy | ✅ implemented | `nexora.security` (`PermissionManager`, `SecretRedactor`) |
| Local storage | ✅ implemented | `nexora.storage` (`LocalStore`, SQLite-backed) |
| Plugin architecture | ✅ implemented | `nexora.plugins` (`Plugin`, feature registry) |
| App / tasks | ✅ implemented | `nexora.App` |
| CLI | ✅ implemented | `nexora` command (`version`, `doctor`, `init`) |
| GhostUI | ✅ implemented | `nexora.ghost` (`GhostPlugin`, `GhostUI`, terminal interfaces via `rich`) |
| CodeWorld | ✅ implemented | `nexora.world` (`WorldPlugin`, `CodeWorld`, 2D entity visualization via `pygame`) |
| MoodUI (adaptive) | ✅ implemented | `nexora.adaptive` (`AdaptivePlugin`, `MoodUI`, interaction-aware states) |
| Recall (memory) | ✅ implemented | `nexora.memory` (`MemoryPlugin`, `Recall`, structured memory via `LocalStore`) |
| TimeLoop (timeline) | ✅ implemented | `nexora.timeline` (`TimelinePlugin`, `TimeLoop`, state checkpoint & rewind) |
| Shadow (observability) | ✅ implemented | `nexora.shadow` (`ShadowPlugin`, `Shadow`, genuine execution timing & errors) |
| ScreenMind (vision) | ✅ implemented | `nexora.vision` (`VisionPlugin`, `ScreenMind`, explicitly-permissioned screen perception) |
| WorldForge | ✅ implemented | `nexora.worldforge` (`WorldForgePlugin`, `WorldForge`, procedural interactive worlds) |
| AgentBox | ✅ implemented | `nexora.agentbox` (`AgentBoxPlugin`, `AgentBox`, sandboxed execution for autonomous agents) |

### Modular Feature Activation

Every feature is strictly optional and isolated. You activate only the modules your application needs:

```python
from nexora import App

# Opt in to only the features you want:
app = App(features=["ghost", "memory", "shadow"])

# Access feature APIs directly on the app instance:
app.memory.remember("server_config", {"port": 8080})
app.ghost.log("App initialized with memory & shadow observability.")
```

If an app requests a planned or unregistered feature that is not available, NEXORA raises a clear `NotImplementedError` rather than silently failing:

```python
app = App(features=["unbuilt_custom_plugin"])
app.run()
# NotImplementedError: NEXORA feature 'unbuilt_custom_plugin' is not registered...
```

See [docs/ROADMAP.md](docs/ROADMAP.md) for the complete roadmap and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the layers fit
together.

## Privacy principles

NEXORA is local-first by default:

- `Config.telemetry` and `Config.cloud_sync` default to `False`.
- `nexora.security.PermissionManager` grants nothing by default -- every
  privacy-sensitive capability future modules add (screen capture, agent
  file/system access, etc.) must be explicitly granted per scope, and
  every grant/revoke is recorded in an in-process audit trail.
- `nexora.storage.LocalStore` is SQLite-backed, on-disk, and makes no
  network calls.
- `nexora.security.SecretRedactor` exists so state/timeline snapshots
  never blindly serialize obvious secret-shaped keys --
  this is a best-effort heuristic, not a guarantee, and callers should
  always add known-sensitive fields explicitly.

See [SECURITY.md](SECURITY.md) for the full policy and responsible
disclosure process.

## Development

```bash
git clone https://github.com/TejaPriyan/Nexora.git
cd Nexora
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how modules are added
incrementally.

## License

MIT -- see [LICENSE](LICENSE).
