"""MoodUI demo: interaction-aware adaptive interface states.

Run with:
    python examples/mood_ui_demo.py

Demonstrates:
- Privacy-first permission gate (explicit opt-in via PermissionManager)
- Observes events flowing on EventBus without emotion-detection claims
- State transitions across NORMAL, FAST, DIFFICULTY_HIGH, ERROR_HEAVY, INACTIVE
- EventBus notifications on 'adaptive.state_changed'
"""

import time
from nexora import App
from nexora.adaptive import InteractionState

# 1. Initialize app with GhostUI and MoodUI (adaptive)
app = App(features=["ghost", "adaptive"])
adaptive = app.adaptive

print("\n" + "=" * 65)
print("  [*] NEXORA MoodUI -- Adaptive Interface Telemetry Demo")
print("=" * 65)

# --- Step 1: Permission Gate Demonstration ---
print("\n[Step 1: Privacy Gate Demonstration]")
print(f"  * Is telemetry permitted by default? {adaptive.is_permitted()} (Zero observation)")

# Attempting an action before permission does not track
app.bus.emit("error", payload={"error": "untracked error before opt-in"})
print(f"  * Current state without permission: {adaptive.current_state.value}")

# Explicit opt-in
print("\n  -> Explicitly granting permission scope 'adaptive.observe'...")
adaptive.opt_in(reason="User enabled adaptive interface in settings")
print(f"  * Is telemetry permitted now? {adaptive.is_permitted()}\n")

# Register a listener for state changes
app.bus.on("adaptive.state_changed", lambda e: print(
    f"  [STATE CHANGE EVENT] {e.payload['previous_state']} -> "
    f"{e.payload['current_state']} | Reason: {e.payload['reason']}"
))


# --- Step 2: Normal Cadence ---
@app.task(name="normal_workflow")
def normal_workflow():
    app.ghost.log("Running baseline workflow...", level="INFO")
    time.sleep(0.05)


# --- Step 3: Fast Cadence (Power User) ---
@app.task(name="rapid_power_user_actions")
def rapid_power_user_actions():
    app.ghost.log("Simulating rapid power-user actions...", level="INFO")
    for i in range(1, 5):
        app.bus.emit("action", payload={"action": f"shortcut_cmd_{i}", "success": True})


# --- Step 4: Friction / Difficulty (Help Request & Repeated Action) ---
@app.task(name="simulate_friction_and_help")
def simulate_friction_and_help():
    app.ghost.log("Simulating user requesting documentation...", level="INFO")
    app.bus.emit("help.requested", payload={"topic": "api_authentication"})


# --- Step 5: Error Heavy (Consecutive Failures) ---
@app.task(name="simulate_repeated_errors")
def simulate_repeated_errors():
    app.ghost.log("Simulating consecutive service failures...", level="INFO")
    for i in range(1, 4):
        app.bus.emit("task.failed", payload={"task": f"database_write_{i}", "error": "Connection reset"})


# --- Step 6: Recovery to Normal ---
@app.task(name="recovery_workflow")
def recovery_workflow():
    app.ghost.log("Recovery actions succeeding...", level="INFO")
    app.bus.emit("action", payload={"action": "reconnect_success", "success": True})
    app.bus.emit("action", payload={"action": "health_check_pass", "success": True})


if __name__ == "__main__":
    app.run()

    print("\n" + "=" * 65)
    print("  Final MoodUI State Transition History:")
    print("=" * 65)
    for i, t in enumerate(adaptive.history, 1):
        print(f"  {i}. {t.from_state.value:<15} -> {t.to_state.value:<15} ({t.reason})")
    print("=" * 65 + "\n")
