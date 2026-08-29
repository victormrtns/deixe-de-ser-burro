from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[3]


@pytest.fixture(scope="module")
def compose_config() -> dict[str, Any]:
    compose_path = REPO_ROOT / "compose.yaml"
    assert compose_path.exists(), "compose.yaml must live at the repository root"
    loaded = yaml.safe_load(compose_path.read_text())
    assert isinstance(loaded, dict)
    return loaded


def test_only_the_frontend_and_loopback_backend_are_externally_bound(
    compose_config: dict[str, Any],
) -> None:
    services = compose_config["services"]

    assert services["db"].get("ports", []) == []
    assert services["backend"].get("ports", []) in ([], ["127.0.0.1:8000:8000"])
    assert services["frontend"]["ports"] == ["127.0.0.1:5173:5173"]
    assert {"db_data", "app_files"} <= set(compose_config["volumes"])


def test_one_shot_commands_are_profile_services(compose_config: dict[str, Any]) -> None:
    services = compose_config["services"]

    for name in ("migrate", "bootstrap-author", "cleanup"):
        assert name in services, f"missing one-shot service: {name}"
        assert services[name].get("profiles") == ["tools"]


def test_the_backend_waits_for_a_healthy_database(compose_config: dict[str, Any]) -> None:
    backend = compose_config["services"]["backend"]

    assert backend["depends_on"]["db"]["condition"] == "service_healthy"
    assert "healthcheck" in compose_config["services"]["db"]


def test_compose_carries_no_secret_values(compose_config: dict[str, Any]) -> None:
    raw = (REPO_ROOT / "compose.yaml").read_text()

    assert "POSTGRES_PASSWORD: " not in raw or "${" in raw
    assert "password123" not in raw.lower()
