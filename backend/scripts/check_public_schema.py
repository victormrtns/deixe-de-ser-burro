"""OpenAPI guard: no private field or schema may appear under /api/public/*.

Run with: uv run python scripts/check_public_schema.py
Exits nonzero listing every violation found.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.main import create_app

PRIVATE_FIELD_NAMES = {
    "id",
    "writingId",
    "writingVersionId",
    "version",
    "versionNumber",
    "status",
    "state",
    "cleanupAt",
    "cleanupDueAt",
    "cleanupCancelledAt",
    "cleanupCompletedAt",
    "messages",
    "audio",
    "transcript",
    "suggestions",
    "privateCoverPath",
    "passwordHash",
    "tokenHash",
    "email",
    "updatedAt",
    "createdAt",
    "expectedVersion",
}
ALLOWED_PUBLIC_SCHEMA_PREFIXES = ("Public", "HTTPValidationError", "ValidationError")


def referenced_schema_names(node: Any, into: set[str]) -> None:
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str):
            into.add(reference.rsplit("/", 1)[-1])
        for value in node.values():
            referenced_schema_names(value, into)
    elif isinstance(node, list):
        for item in node:
            referenced_schema_names(item, into)


def closure_of_schemas(names: set[str], components: dict[str, Any]) -> set[str]:
    resolved: set[str] = set()
    pending = set(names)
    while pending:
        name = pending.pop()
        if name in resolved:
            continue
        resolved.add(name)
        nested: set[str] = set()
        referenced_schema_names(components.get(name, {}), nested)
        pending |= nested - resolved
    return resolved


def property_names(schema: dict[str, Any]) -> set[str]:
    names = set(schema.get("properties", {}))
    for nested_key in ("items", "additionalProperties"):
        nested = schema.get(nested_key)
        if isinstance(nested, dict):
            names |= property_names(nested)
    for variant_key in ("anyOf", "oneOf", "allOf"):
        for variant in schema.get(variant_key, []):
            if isinstance(variant, dict):
                names |= property_names(variant)
    return names


def main() -> int:
    specification = create_app().openapi()
    components: dict[str, Any] = specification.get("components", {}).get("schemas", {})
    violations: list[str] = []

    for path, operations in specification["paths"].items():
        if not path.startswith("/api/public/"):
            continue
        direct_references: set[str] = set()
        referenced_schema_names(operations, direct_references)
        for name in closure_of_schemas(direct_references, components):
            if not name.startswith(ALLOWED_PUBLIC_SCHEMA_PREFIXES):
                violations.append(f"{path}: referencia schema privado {name}")
                continue
            if name.startswith("Public"):
                leaked = property_names(components.get(name, {})) & PRIVATE_FIELD_NAMES
                if leaked:
                    violations.append(f"{path}: {name} expõe campos privados {sorted(leaked)}")

    if violations:
        print("Violações de privacidade no schema público:")
        for violation in sorted(set(violations)):
            print(f"  - {violation}")
        return 1

    print("Schema público sem campos ou referências privadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
