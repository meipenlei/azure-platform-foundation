#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ASSET_DIRS = (
    "archetype_definitions",
    "policy_assignments",
    "policy_definitions",
    "policy_set_definitions",
    "role_definitions",
)


class InventoryError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory a legacy ALZ-style Azure Policy library."
    )
    parser.add_argument(
        "--library-dir",
        type=Path,
        required=True,
        help="Path containing the ALZ-style policy library directories.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to write the complete inventory JSON.",
    )
    return parser.parse_args()


def json_files(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".json"
        and path.name.lower() != "readme.md"
    )


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryError(f"Unable to parse {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise InventoryError(f"{path} must contain a JSON object.")

    return data


def classify_reference(reference: str) -> str:
    if "${root_scope_resource_id}" in reference:
        return "root-scope-library"
    if "/providers/Microsoft.Authorization/policyDefinitions/" in reference:
        return "built-in-policy"
    if "/providers/Microsoft.Authorization/policySetDefinitions/" in reference:
        return "built-in-policy-set"
    return "other"


def build_inventory(library_dir: Path) -> dict[str, Any]:
    if not library_dir.is_dir():
        raise InventoryError(f"Library directory does not exist: {library_dir}")

    missing = [
        name
        for name in ASSET_DIRS
        if not (library_dir / name).is_dir()
    ]
    if missing:
        raise InventoryError(
            "Library is missing required directories: " + ", ".join(missing)
        )

    inventory: dict[str, Any] = {
        "schema_version": "0.1",
        "library_dir": str(library_dir.resolve()),
        "counts": {},
        "archetypes": {},
        "assignments": [],
        "custom_policy_definitions": [],
        "custom_policy_set_definitions": [],
        "custom_role_definitions": [],
    }

    files_by_dir: dict[str, list[Path]] = {}
    for name in ASSET_DIRS:
        files = json_files(library_dir / name)
        files_by_dir[name] = files
        inventory["counts"][name] = len(files)

    for path in files_by_dir["archetype_definitions"]:
        doc = load_json(path)
        for archetype_id, value in doc.items():
            if not isinstance(value, dict):
                continue
            inventory["archetypes"][archetype_id] = {
                "file": path.name,
                "policy_assignments": list(
                    value.get("policy_assignments", [])
                ),
                "policy_definitions": list(
                    value.get("policy_definitions", [])
                ),
                "policy_set_definitions": list(
                    value.get("policy_set_definitions", [])
                ),
                "role_definitions": list(
                    value.get("role_definitions", [])
                ),
            }

    for path in files_by_dir["policy_assignments"]:
        doc = load_json(path)
        props = doc.get("properties", {})
        if not isinstance(props, dict):
            props = {}

        identity = doc.get("identity", {})
        identity_type = None
        if isinstance(identity, dict):
            identity_type = identity.get("type")

        reference = str(props.get("policyDefinitionId", ""))

        inventory["assignments"].append(
            {
                "file": path.name,
                "name": doc.get("name"),
                "display_name": props.get("displayName"),
                "policy_definition_id": reference,
                "reference_kind": classify_reference(reference),
                "enforcement_mode": props.get("enforcementMode"),
                "identity_type": identity_type,
                "parameter_names": sorted(
                    (props.get("parameters") or {}).keys()
                )
                if isinstance(props.get("parameters") or {}, dict)
                else [],
            }
        )

    for source, target in (
        ("policy_definitions", "custom_policy_definitions"),
        ("policy_set_definitions", "custom_policy_set_definitions"),
        ("role_definitions", "custom_role_definitions"),
    ):
        for path in files_by_dir[source]:
            doc = load_json(path)
            props = doc.get("properties", {})
            if not isinstance(props, dict):
                props = {}
            inventory[target].append(
                {
                    "file": path.name,
                    "name": doc.get("name"),
                    "display_name": props.get("displayName")
                    or props.get("roleName"),
                    "api_version": doc.get("apiVersion"),
                }
            )

    return inventory


def print_summary(inventory: dict[str, Any]) -> None:
    counts = inventory["counts"]

    print("APF legacy policy library inventory")
    print("-----------------------------------")
    for name in ASSET_DIRS:
        print(f"{name:24} {counts[name]:>4}")

    print()
    print(f"archetypes discovered: {len(inventory['archetypes'])}")
    print(f"assignments discovered: {len(inventory['assignments'])}")


def main() -> int:
    args = parse_args()

    try:
        inventory = build_inventory(args.library_dir)
        print_summary(inventory)

        if args.output_json:
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            args.output_json.write_text(
                json.dumps(inventory, indent=2) + "\n",
                encoding="utf-8",
            )
            print()
            print(f"[PASS] Inventory written to {args.output_json}")

        return 0

    except InventoryError as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
