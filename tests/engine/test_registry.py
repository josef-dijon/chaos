import pytest
from chaos.domain.messages import Request
from chaos.engine.registry import RepairRegistry


def test_registry_registration():
    @RepairRegistry.register("test_func")
    def func(req, fail):
        return req

    assert RepairRegistry.get("test_func") == func
    RepairRegistry.clear()


def test_registry_get_missing():
    with pytest.raises(ValueError):
        RepairRegistry.get("missing_func")


def test_registry_clear():
    @RepairRegistry.register("test_func")
    def func(req, fail):
        return req

    RepairRegistry.clear()
    with pytest.raises(ValueError):
        RepairRegistry.get("test_func")
