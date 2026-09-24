"""Recall (memory) demo: structured, persistent, local-first application memory.

Run with:
    python examples/recall_demo.py
"""

from nexora import App

# Start App with GhostUI and Recall (memory)
app = App(features=["ghost", "memory"])
memory = app.memory

print("\n" + "=" * 65)
print("  [*] NEXORA Recall -- Persistent Application Memory Demo")
print("=" * 65)

# Step 1: Remembering structured facts with automatic secret redaction
print("\n[Step 1: Storing Memories with Secret Redaction]")
item1 = memory.remember(
    "database_cluster",
    value={
        "host": "db.internal.net",
        "port": 5432,
        "database": "analytics",
        "password": "production_super_secret_pass",
        "api_key": "sk-secret-key-999",
    },
    tags=["db", "infra", "postgres"],
)
print(f"  * Stored: {item1.id}")
print(f"  * Value (secrets scrubbed): {item1.value}")

item2 = memory.remember(
    "api_deployment",
    value="Deployed v2.4.0 to production us-east-1 on port 8080",
    tags=["deploy", "api"],
)
print(f"  * Stored: {item2.id} -> {item2.value}")

# Step 2: Searching memories
print("\n[Step 2: Searching Memories by Query & Tags]")
results = memory.search("postgres", tags=["infra"])
for r in results:
    print(f"  * Search match: [{r.id}] (tags: {r.tags})")

# Step 3: Local Retrieval Question Answering (No external API needed)
print("\n[Step 3: Local Question Answering ('ask')]")
for q in ["Where is database cluster?", "What is api deployment status?"]:
    answer = memory.ask(q)
    print(f"  * Q: {q}")
    print(f"    A: {answer}")

# Step 4: Chronological Timeline
print("\n[Step 4: Memory Timeline]")
for idx, m in enumerate(memory.timeline(), 1):
    print(f"  {idx}. [{m.id}] (timestamp={m.timestamp:.2f})")

print("=" * 65 + "\n")
