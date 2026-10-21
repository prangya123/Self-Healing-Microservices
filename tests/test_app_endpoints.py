import importlib
import os

from fastapi.testclient import TestClient


def test_dependency_service_admin_disabled_without_test_mode():
    os.environ.pop("SELF_HEALING_TEST_MODE", None)
    import src.app.dependency_service as dep
    importlib.reload(dep)
    client = TestClient(dep.app)
    r = client.post("/admin/inject_timeout", params={"enabled": True})
    assert r.status_code == 403


def test_dependency_service_admin_enabled_with_test_mode():
    os.environ["SELF_HEALING_TEST_MODE"] = "1"
    import src.app.dependency_service as dep
    importlib.reload(dep)
    client = TestClient(dep.app)
    r = client.post("/admin/inject_timeout", params={"enabled": True, "delay_seconds": 0.0, "failure_rate": 1.0})
    assert r.status_code == 200
    r2 = client.get("/ping")
    assert r2.status_code == 503
    os.environ.pop("SELF_HEALING_TEST_MODE", None)
    importlib.reload(dep)


def test_main_service_health_reports_process_stats():
    import src.app.main_service as main
    importlib.reload(main)
    client = TestClient(main.app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "cpu_percent" in body and "mem_mb" in body
    assert body["circuit_breaker_open"] is False


def test_main_service_memory_leak_disabled_without_test_mode():
    os.environ.pop("SELF_HEALING_TEST_MODE", None)
    import src.app.main_service as main
    importlib.reload(main)
    client = TestClient(main.app)
    r = client.post("/admin/memory_leak/start")
    assert r.status_code == 403


def test_main_service_circuit_breaker_produces_degraded_fallback():
    import src.app.main_service as main
    importlib.reload(main)
    client = TestClient(main.app)
    r = client.post("/admin/circuit_breaker", params={"open": True})
    assert r.status_code == 200
    r2 = client.get("/work")
    assert r2.status_code == 200
    assert r2.json()["mode"] == "degraded_fallback"
    client.post("/admin/circuit_breaker", params={"open": False})
