from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
OPS = REPO_ROOT / "ops"


def read(name: str) -> str:
    path = OPS / name
    assert path.exists(), f"missing ops file: {name}"
    return path.read_text()


def test_backup_scripts_require_encryption_and_a_remote_destination() -> None:
    for name in ("backup-postgres.sh", "backup-files.sh"):
        script = read(name)
        assert "set -euo pipefail" in script
        assert "age" in script
        assert "BACKUP_REMOTE" in script
        assert "AGE_RECIPIENT" in script
        assert "mktemp -d" in script
        assert "sha256sum" in script


def test_the_restore_smoke_uses_a_disposable_uniquely_named_database() -> None:
    script = read("restore-smoke.sh")

    assert "set -euo pipefail" in script
    assert "TEST_RESTORE" in script
    assert "restore_smoke_" in script
    assert "DROP DATABASE" in script or "dropdb" in script
    assert "mktemp -d" in script


def test_the_cleanup_timer_runs_the_one_shot_command_at_least_hourly() -> None:
    service = read("cleanup.service")
    timer = read("cleanup.timer")

    assert "docker compose run --rm cleanup" in service
    assert "OnCalendar=hourly" in timer or "OnUnitActiveSec" in timer
    assert "Persistent=true" in timer


def test_the_deploy_runbook_orders_backup_before_migrate_before_start() -> None:
    runbook = read("deploy.md").lower()

    backup = runbook.index("## 1. backup")
    migrate = runbook.index("## 2. migra")
    start = runbook.index("## 3. subir")
    readiness = runbook.index("## 4. readiness")

    assert backup < migrate < start < readiness
