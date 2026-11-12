#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


POLICY_ASSIGNMENT_RESOURCE = (
    "/providers/Microsoft.Authorization/policyAssignments/"
)


class PlanVerificationError(RuntimeError):
    pass


class RetryableConvergenceError(PlanVerificationError):
    """Azure read-after-write propagation may not have converged yet."""

    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that an EPAC deployment plan stays inside the APF "
            "protected policy-apply boundary."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("pre-apply", "post-apply"),
        required=True,
    )
    parser.add_argument(
        "--definitions-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--pac-selector",
        required=True,
    )
    parser.add_argument(
        "--policy-plan",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--roles-plan",
        type=Path,
        required=True,
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanVerificationError(
            f"Unable to read JSON '{path}': {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise PlanVerificationError(
            f"JSON '{path}' must contain an object."
        )

    return data


def optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return load_json(path)


def collection_count(value: Any, *, label: str) -> int:
    if value is None:
        return 0
    if isinstance(value, (dict, list)):
        return len(value)
    raise PlanVerificationError(
        f"EPAC plan field '{label}' must be an object or array."
    )


def resource_change_count(
    section: dict[str, Any],
    *,
    section_name: str,
) -> int:
    total = 0
    for action in ("new", "update", "replace", "delete"):
        total += collection_count(
            section.get(action),
            label=f"{section_name}.{action}",
        )
    return total


def global_settings(definitions_root: Path) -> dict[str, Any]:
    return load_json(definitions_root / "global-settings.jsonc")


def expected_assignment_ids(
    definitions_root: Path,
    pac_selector: str,
) -> set[str]:
    assignment_dir = definitions_root / "policyAssignments"
    if not assignment_dir.is_dir():
        raise PlanVerificationError(
            f"Policy assignments folder not found: {assignment_dir}"
        )

    expected: set[str] = set()

    for path in sorted(assignment_dir.glob("*.assignment.jsonc")):
        document = load_json(path)

        assignment = document.get("assignment")
        scope = document.get("scope")
        if not isinstance(assignment, dict) or not isinstance(scope, dict):
            raise PlanVerificationError(
                f"Assignment source '{path}' is missing assignment/scope."
            )

        name = assignment.get("name")
        scopes = scope.get(pac_selector)

        if not isinstance(name, str) or not name:
            raise PlanVerificationError(
                f"Assignment source '{path}' has no assignment name."
            )
        if not isinstance(scopes, list) or not scopes:
            raise PlanVerificationError(
                f"Assignment source '{path}' has no scope for "
                f"PAC selector '{pac_selector}'."
            )

        for item in scopes:
            if not isinstance(item, str) or not item.startswith("/"):
                raise PlanVerificationError(
                    f"Assignment source '{path}' contains invalid scope: "
                    f"{item!r}"
                )
            resource_id = (
                item.rstrip("/")
                + POLICY_ASSIGNMENT_RESOURCE
                + name
            )
            expected.add(resource_id.lower())

    if not expected:
        raise PlanVerificationError(
            "No generated assignment resource IDs were discovered."
        )

    return expected


def verify_owner(
    plan: dict[str, Any],
    *,
    expected_owner: str,
    label: str,
) -> None:
    actual_owner = plan.get("pacOwnerId")
    if actual_owner != expected_owner:
        raise PlanVerificationError(
            f"{label} pacOwnerId mismatch. Expected {expected_owner!r}, "
            f"found {actual_owner!r}."
        )


def verify_policy_plan(
    plan: dict[str, Any] | None,
    *,
    expected_owner: str,
    expected_assignments: set[str],
    mode: str,
) -> int:
    if plan is None:
        return 0

    verify_owner(
        plan,
        expected_owner=expected_owner,
        label="Policy plan",
    )

    for section_name in (
        "policyDefinitions",
        "policySetDefinitions",
        "exemptions",
        "enrollments",
    ):
        section = plan.get(section_name) or {}
        if not isinstance(section, dict):
            raise PlanVerificationError(
                f"Policy plan section '{section_name}' must be an object."
            )
        count = resource_change_count(
            section,
            section_name=section_name,
        )
        if count:
            raise PlanVerificationError(
                f"Protected apply rejects {count} change(s) in "
                f"'{section_name}'."
            )

    assignments = plan.get("assignments") or {}
    if not isinstance(assignments, dict):
        raise PlanVerificationError(
            "Policy plan assignments section must be an object."
        )

    for action in ("update", "replace", "delete"):
        count = collection_count(
            assignments.get(action),
            label=f"assignments.{action}",
        )
        if count:
            raise PlanVerificationError(
                f"Protected apply rejects {count} assignment "
                f"{action} change(s)."
            )

    new_assignments = assignments.get("new") or {}
    if not isinstance(new_assignments, dict):
        raise PlanVerificationError(
            "Policy plan assignments.new must be an object."
        )

    planned_ids = {str(item).lower() for item in new_assignments.keys()}
    unexpected = sorted(planned_ids - expected_assignments)
    if unexpected:
        raise PlanVerificationError(
            "Protected apply contains assignment IDs not present in the "
            "generated Definitions tree:\n  - "
            + "\n  - ".join(unexpected)
        )

    if mode == "post-apply" and planned_ids:
        raise RetryableConvergenceError(
            "Post-apply verification still contains expected new policy "
            "assignments; Azure may still be converging: "
            + ", ".join(sorted(planned_ids))
        )

    return len(planned_ids)


def verify_roles_plan(
    plan: dict[str, Any] | None,
    *,
    expected_owner: str,
) -> int:
    if plan is None:
        return 0

    verify_owner(
        plan,
        expected_owner=expected_owner,
        label="Roles plan",
    )

    roles = plan.get("roleAssignments") or {}
    if not isinstance(roles, dict):
        raise PlanVerificationError(
            "Roles plan roleAssignments section must be an object."
        )

    total = 0
    for action in ("added", "updated", "removed"):
        total += collection_count(
            roles.get(action),
            label=f"roleAssignments.{action}",
        )

    if total:
        raise PlanVerificationError(
            f"Protected apply rejects {total} role assignment change(s)."
        )

    return total


def verify(args: argparse.Namespace) -> tuple[int, int]:
    settings = global_settings(args.definitions_root)
    owner = settings.get("pacOwnerId")
    if not isinstance(owner, str) or not owner:
        raise PlanVerificationError(
            "global-settings.jsonc does not contain pacOwnerId."
        )

    expected = expected_assignment_ids(
        args.definitions_root,
        args.pac_selector,
    )

    policy_plan = optional_json(args.policy_plan)
    roles_plan = optional_json(args.roles_plan)

    policy_changes = verify_policy_plan(
        policy_plan,
        expected_owner=owner,
        expected_assignments=expected,
        mode=args.mode,
    )
    role_changes = verify_roles_plan(
        roles_plan,
        expected_owner=owner,
    )

    if args.mode == "post-apply" and (policy_changes or role_changes):
        raise PlanVerificationError(
            "Post-apply EPAC desired state has not converged."
        )

    return policy_changes, role_changes


def main() -> int:
    args = parse_args()

    try:
        policy_changes, role_changes = verify(args)
        if args.mode == "pre-apply":
            print("[PASS] EPAC protected apply boundary verified.")
            print(
                f"[PASS] Allowed new policy assignments: {policy_changes}."
            )
            print(
                f"[PASS] Role assignment changes: {role_changes}."
            )
        else:
            print("[PASS] EPAC post-apply convergence verified.")
            print("[PASS] Remaining policy changes: 0.")
            print("[PASS] Remaining role changes: 0.")
        return 0
    except RetryableConvergenceError as exc:
        print(f"[RETRY] {exc}", file=sys.stderr)
        return 3
    except (PlanVerificationError, OSError, KeyError, TypeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
