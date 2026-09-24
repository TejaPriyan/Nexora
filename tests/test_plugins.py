import pytest

from nexora.plugins import UnknownFeatureError, available_features, resolve


def test_all_documented_features_resolve():
    for name in available_features():
        cls = resolve(name)
        assert cls.name == name


def test_unknown_feature():
    with pytest.raises(UnknownFeatureError):
        resolve("does-not-exist")
