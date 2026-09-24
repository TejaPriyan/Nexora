from nexora.storage import LocalStore


def test_set_get_roundtrip(tmp_path):
    store = LocalStore("test", base_dir=tmp_path)
    store.set("a", {"nested": [1, 2, 3]})
    assert store.get("a") == {"nested": [1, 2, 3]}
    store.close()


def test_namespaces_are_isolated(tmp_path):
    store = LocalStore("test", base_dir=tmp_path)
    store.set("k", "ns1-value", namespace="ns1")
    store.set("k", "ns2-value", namespace="ns2")
    assert store.get("k", namespace="ns1") == "ns1-value"
    assert store.get("k", namespace="ns2") == "ns2-value"
    store.close()


def test_delete_and_default(tmp_path):
    store = LocalStore("test", base_dir=tmp_path)
    store.set("k", "v")
    store.delete("k")
    assert store.get("k", default="missing") == "missing"
    store.close()


def test_keys_and_items(tmp_path):
    store = LocalStore("test", base_dir=tmp_path)
    store.set("a", 1)
    store.set("b", 2)
    assert set(store.keys()) == {"a", "b"}
    assert dict(store.items()) == {"a": 1, "b": 2}
    store.close()


def test_persists_across_instances(tmp_path):
    store1 = LocalStore("persist", base_dir=tmp_path)
    store1.set("k", "v")
    store1.close()
    store2 = LocalStore("persist", base_dir=tmp_path)
    assert store2.get("k") == "v"
    store2.close()
