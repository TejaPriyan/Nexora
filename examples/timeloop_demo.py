"""TimeLoop demo: checkpoint, snapshot, diff, rewind, and restore.

Run with:
    python examples/timeloop_demo.py
"""

from nexora import App

app = App(features=["ghost", "timeline"])
timeline = app.timeline

# Configure custom secret exclusion
timeline.ignore("custom_signing_key")

print("\n" + "=" * 65)
print("  [*] NEXORA TimeLoop -- Runtime State Git & Rewind Demo")
print("=" * 65)

# Step 1: Initial state checkpoint with secrets
print("\n[Step 1: Creating Checkpoints with Secret Redaction]")
app.state.set("user", "developer")
app.state.set("env", "staging")
app.state.set("password", "plaintext_secret_1234")
app.state.set("custom_signing_key", "sign_abc_999")

c1 = timeline.checkpoint("v1_initial")
print(f"  * Checkpoint 1: [{c1.id}] '{c1.label}'")
print(f"  * Data (redacted): {c1.data}")

# Step 2: Modifying state and creating checkpoint 2
print("\n[Step 2: Updating State and Computing Diff]")
app.state.set("env", "production")
app.state.set("database_pool", 25)
c2 = timeline.checkpoint("v2_promoted")
print(f"  * Checkpoint 2: [{c2.id}] '{c2.label}'")
print(f"  * Data: {c2.data}")

# Diff
diff = timeline.diff(c1.id, c2.id)
print("\n[Structural Diff (v1 -> v2)]")
print(f"  * Added keys   : {diff.added}")
print(f"  * Changed keys : {diff.changed}")

# Step 3: Rewind
print("\n[Step 3: Rewinding State by 1 Step]")
print(f"  * State before rewind: env={app.state.get('env')}")
rewound = timeline.rewind(1)
print(f"  * Rewound to: [{rewound.id}] '{rewound.label}'")
print(f"  * State after rewind : env={app.state.get('env')}")

# Step 4: Fast-forward / Restore
print("\n[Step 4: Restoring Checkpoint by ID]")
timeline.restore(c2.id)
print(f"  * Restored to v2: env={app.state.get('env')}, database_pool={app.state.get('database_pool')}")

print("\n" + "=" * 65)
print("  TimeLoop Checkpoint History:")
print("=" * 65)
for idx, s in enumerate(timeline.history(), 1):
    print(f"  {idx}. [{s.id}] {s.label:<18} (timestamp={s.timestamp:.2f}, keys={len(s.data)})")
print("=" * 65 + "\n")
