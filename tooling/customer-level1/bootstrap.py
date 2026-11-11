#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import yaml


STATE_DATA_ROLE = "Storage Blob Data Contributor"
ROOT_RELATIVE = Path("levels/level1/management-groups")
SNAPSHOT_RELATIVE = Path(".foundation/level1-management-groups.yaml")


class BootstrapError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap the APF Level 1 management-group hierarchy using the "
            "currently signed-in Azure operator."
        )
    )
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the Terraform plan. Without this flag only plan is executed.",
    )
    return parser.parse_args()


def run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command))

    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    result = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture_output,
        check=False,
        env=process_env,
    )

    if check and result.returncode != 0:
        details = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )
        raise BootstrapError(
            f"Command failed ({result.returncode}): {' '.join(command)}"
            + (f"\n{details}" if details else "")
        )
    return result


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise BootstrapError(f"Required command '{name}' was not found in PATH.")


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise BootstrapError(f"Unable to read YAML '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise BootstrapError(f"YAML '{path}' must contain an object.")
    return data


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapError(f"Unable to read JSON '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise BootstrapError(f"JSON '{path}' must contain an object.")
    return data


def verify_project(project_dir: Path) -> tuple[Path, dict, dict]:
    root = project_dir / ROOT_RELATIVE
    required = (
        root / "versions.tf",
        root / "providers.tf",
        root / "variables.tf",
        root / "main.tf",
        root / "outputs.tf",
        root / "backend.tf",
        root / "backend.hcl",
        root / "generated.auto.tfvars.json",
        project_dir / ".foundation/level0-bootstrap.yaml",
    )
    missing = [
        str(path.relative_to(project_dir))
        for path in required
        if not path.is_file()
    ]
    if missing:
        raise BootstrapError(
            "Level 1 project is incomplete:\n  - " + "\n  - ".join(missing)
        )

    return (
        root,
        load_json(root / "generated.auto.tfvars.json"),
        load_yaml(project_dir / ".foundation/level0-bootstrap.yaml"),
    )


def verify_azure_context(tfvars: dict[str, Any]) -> None:
    result = run(
        ["az", "account", "show", "--output", "json"],
        capture_output=True,
    )
    try:
        account = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BootstrapError("Azure CLI returned invalid account JSON.") from exc

    if str(account.get("tenantId")) != str(tfvars["tenant_id"]):
        raise BootstrapError("Azure CLI tenant does not match Level 1 configuration.")
    if str(account.get("id")) != str(tfvars["subscription_id"]):
        raise BootstrapError(
            "Azure CLI subscription does not match Level 1 configuration."
        )

    print("[PASS] Azure CLI tenant and subscription match Level 1 configuration.")


def signed_in_user_object_id() -> str:
    result = run(
        [
            "az",
            "ad",
            "signed-in-user",
            "show",
            "--query",
            "id",
            "--output",
            "tsv",
        ],
        capture_output=True,
    )
    object_id = result.stdout.strip()
    if not object_id:
        raise BootstrapError("Unable to determine signed-in Azure user object ID.")
    return object_id


def find_state_role_assignment(*, principal_id: str, scope: str) -> str | None:
    result = run(
        [
            "az",
            "role",
            "assignment",
            "list",
            "--assignee",
            principal_id,
            "--scope",
            scope,
            "--query",
            f"[?roleDefinitionName=='{STATE_DATA_ROLE}'].id | [0]",
            "--output",
            "tsv",
        ],
        capture_output=True,
    )
    assignment_id = result.stdout.strip()
    return assignment_id or None


def create_temporary_state_access(*, principal_id: str, scope: str) -> str:
    result = run(
        [
            "az",
            "role",
            "assignment",
            "create",
            "--assignee-object-id",
            principal_id,
            "--assignee-principal-type",
            "User",
            "--role",
            STATE_DATA_ROLE,
            "--scope",
            scope,
            "--query",
            "id",
            "--output",
            "tsv",
        ],
        capture_output=True,
    )
    assignment_id = result.stdout.strip()
    if not assignment_id:
        raise BootstrapError("Temporary state access role assignment returned no ID.")
    print("[PASS] Temporary Terraform state access granted.")
    return assignment_id


def delete_temporary_state_access(assignment_id: str) -> None:
    run(["az", "role", "assignment", "delete", "--ids", assignment_id])
    print("[PASS] Temporary Terraform state access removed.")


def wait_for_state_access(*, storage_account_name: str, container_name: str) -> None:
    for _ in range(60):
        result = run(
            [
                "az",
                "storage",
                "blob",
                "list",
                "--auth-mode",
                "login",
                "--account-name",
                storage_account_name,
                "--container-name",
                container_name,
                "--num-results",
                "1",
                "--only-show-errors",
                "--output",
                "none",
            ],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            print("[PASS] Terraform state data-plane access is effective.")
            return

        print("Terraform state access is not effective yet; retrying...")
        time.sleep(10)

    raise BootstrapError(
        "Temporary Terraform state access did not become effective within 10 minutes."
    )


def terraform_outputs(root: Path) -> dict[str, Any]:
    result = run(["terraform", "output", "-json"], cwd=root, capture_output=True)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BootstrapError("Terraform returned invalid output JSON.") from exc
    if not isinstance(data, dict):
        raise BootstrapError("Terraform returned unexpected output data.")
    return data


def output_value(outputs: dict[str, Any], name: str) -> Any:
    entry = outputs.get(name)
    if not isinstance(entry, dict):
        return None
    return entry.get("value")


def write_snapshot(project_dir: Path, outputs: dict[str, Any]) -> None:
    required = (
        "root_management_group_id",
        "root_management_group_name",
        "management_group_ids",
        "bootstrap_subscription_parent_management_group_id",
        "policy_deployment_root_scope",
    )
    missing = [
        name
        for name in required
        if output_value(outputs, name) in (None, "")
    ]
    if missing:
        raise BootstrapError(
            "Unable to write Level 1 snapshot. Missing outputs: "
            + ", ".join(missing)
        )

    payload = {
        "schema_version": "0.1",
        "source": "terraform-level1-management-groups",
        "management_groups": {
            name: output_value(outputs, name)
            for name in required
        },
    }

    target = project_dir / SNAPSHOT_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    print(f"[PASS] Generated {SNAPSHOT_RELATIVE}.")


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.resolve()

    print("Azure Platform Foundation Level 1 bootstrap")
    print("-------------------------------------------")
    print(f"Project: {project_dir}")
    print(f"Mode:    {'apply' if args.apply else 'plan'}")
    print()

    temporary_assignment_id: str | None = None
    main_error: Exception | None = None
    cleanup_error: Exception | None = None
    exit_code = 0

    try:
        require_command("terraform")
        require_command("az")

        root, tfvars, level0 = verify_project(project_dir)
        verify_azure_context(tfvars)

        bootstrap = level0["bootstrap"]
        state_scope = str(bootstrap["state_container_id"])
        user_object_id = signed_in_user_object_id()

        existing_assignment = find_state_role_assignment(
            principal_id=user_object_id,
            scope=state_scope,
        )
        if existing_assignment:
            print("[PASS] Signed-in user already has Terraform state access.")
        else:
            temporary_assignment_id = create_temporary_state_access(
                principal_id=user_object_id,
                scope=state_scope,
            )
            wait_for_state_access(
                storage_account_name=str(bootstrap["storage_account_name"]),
                container_name=str(bootstrap["state_container_name"]),
            )

        print()
        print("Initializing Level 1 management-group state...")
        run(
            [
                "terraform",
                "init",
                "-upgrade",
                "-reconfigure",
                "-backend-config=backend.hcl",
            ],
            cwd=root,
        )

        print()
        print("Validating Level 1 management groups...")
        run(["terraform", "fmt", "-check", "-recursive"], cwd=root)
        run(["terraform", "validate"], cwd=root)

        plan_path = root / ".apf-level1-management-groups.tfplan"
        if plan_path.exists():
            plan_path.unlink()

        print()
        print("Planning Level 1 management groups...")
        run(
            [
                "terraform",
                "plan",
                "-lock-timeout=5m",
                "-out=.apf-level1-management-groups.tfplan",
            ],
            cwd=root,
        )

        if not args.apply:
            print()
            print("Level 1 plan completed successfully.")
            print("No Level 1 Azure changes were applied.")
        else:
            print()
            print("Applying Level 1 management groups...")
            run(
                ["terraform", "apply", "-auto-approve", plan_path.name],
                cwd=root,
            )

            outputs = terraform_outputs(root)
            write_snapshot(project_dir, outputs)

            state = run(
                ["terraform", "state", "list"],
                cwd=root,
                capture_output=True,
            )
            resources = [
                line.strip()
                for line in state.stdout.splitlines()
                if line.strip()
            ]
            if not resources:
                raise BootstrapError(
                    "Level 1 remote state is readable but contains no resources."
                )

            print(
                f"[PASS] Level 1 remote state is readable "
                f"({len(resources)} state entries)."
            )
            print("[PASS] Level 1 management-group bootstrap completed.")

    except Exception as exc:
        main_error = exc
        exit_code = 2

    finally:
        if temporary_assignment_id:
            try:
                delete_temporary_state_access(temporary_assignment_id)
            except Exception as exc:
                cleanup_error = exc
                exit_code = 2

    if main_error:
        print(f"[ERROR] {main_error}", file=sys.stderr)
    if cleanup_error:
        print(
            f"[ERROR] Temporary state-access cleanup failed: {cleanup_error}",
            file=sys.stderr,
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
