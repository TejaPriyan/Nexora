"""Demonstration of Shadow (live observability) in NEXORA."""

import time
from nexora import App


def main() -> None:
    app = App(features=["shadow"])
    shadow = app.shadow
    assert shadow is not None

    print("=== NEXORA Shadow Observability Demo ===")

    @shadow.trace
    def fetch_user_data(user_id: int) -> dict:
        time.sleep(0.02)
        return {"id": user_id, "name": f"User_{user_id}"}

    @shadow.trace
    def process_order(user_id: int, amount: float) -> str:
        user = fetch_user_data(user_id)
        time.sleep(0.01)
        if amount <= 0:
            raise ValueError(f"Invalid order amount: {amount}")
        return f"Order processed for {user['name']} of ${amount:.2f}"

    # Normal executions
    print("Executing operations...")
    print(" - Result 1:", process_order(101, 49.99))
    print(" - Result 2:", process_order(102, 19.50))

    # Error execution
    print("Executing failing operation...")
    try:
        process_order(103, -10.00)
    except ValueError as err:
        print(" - Caught expected error:", err)

    # Context manager span
    with shadow.span("cache_cleanup"):
        time.sleep(0.01)
        print(" - Performed cache cleanup")

    # Inspect function statistics
    print("\n--- Observed Function Profiles ---")
    stats = shadow.function_stats()
    for name, prof in stats.items():
        print(f"[{name}]")
        print(f"  Calls: {prof.call_count} | Errors: {prof.error_count}")
        print(f"  Avg time: {prof.avg_duration * 1000:.2f} ms")
        print(f"  Min time: {prof.min_duration * 1000:.2f} ms | Max time: {prof.max_duration * 1000:.2f} ms")

    # Inspect dependencies
    print("\n--- Observed Dependencies ---")
    for dep in shadow.dependencies():
        print(f"  {dep.caller} -> {dep.callee} ({dep.call_count} calls)")

    # Inspect captured errors
    print("\n--- Observed Errors ---")
    for err in shadow.errors():
        print(f"  [{err.error_type}] in {err.source}: {err.message}")

    print("\nShadow observability completed successfully!")


if __name__ == "__main__":
    main()
