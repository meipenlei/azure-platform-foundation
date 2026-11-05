#!/usr/bin/env python3

"""
Azure Platform Foundation customer bootstrap lifecycle.

This tool operates on a generated APF customer repository.

Commit 4 scope:
- validates local prerequisites and generated Level 0 bootstrap inputs
- validates the active Azure CLI tenant/subscription context
- initializes and validates the Level 0 bootstrap Terraform root
- creates a Terraform bootstrap plan
- applies the bootstrap only when --apply is supplied
- reads bootstrap outputs
- creates backend.tf/backend.hcl for the bootstrap root
- creates backend.hcl for the governance root
- temporarily grants the signed-in bootstrap user state-container access
  when needed
- migrates the Level 0 bootstrap state from local state to Azure
- verifies that the migrated remote state is readable
- removes temporary state-container access by default

Commit 5 additionally supports an explicit governance handover:
- derives governance Terraform inputs from bootstrap outputs
- initializes the separate governance state
- plans governance changes with the local privileged bootstrap operator
- applies governance changes only when both --governance and --apply are used
- verifies the governance remote state after apply
"""

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


TERRAFORM_REQUIRED_VERSION_PREFIX = "Terraform v1.17."
STATE_DATA_ROLE = "Storage Blob Data Contributor"

BOOTSTRAP_STATE_KEY = "level0.bootstrap.tfstate"
GOVERNANCE_STATE_KEY = "level0.governance.tfstate"

BOOTSTRAP_BACKEND_TF = """\
terraform {
  backend "azurerm" {}
}
"""


class BootstrapError(RuntimeError):
    """Raised for an APF bootstrap lifecycle failure."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap a generated Azure Platform Foundation customer project."
        )
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path("."),
        help=(
            "Generated APF customer repository. "
            "Defaults to the current directory."
        ),
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Apply the bootstrap plan and perform backend/state migration. "
            "Without this flag the tool stops after terraform plan."
        ),
    )

    parser.add_argument(
        "--keep-temporary-state-access",
        action="store_true",
        help=(
            "Do not remove a temporary Storage Blob Data Contributor role "
            "assignment created for the signed-in bootstrap user."
        ),
    )

    parser.add_argument(
        "--governance",
        action="store_true",
        help=(
            "Continue with the Level 0 governance handover after the "
            "bootstrap phase. Without --apply this performs a governance "
            "plan only. With --apply it also applies governance."
        ),
    )

    return parser.parse_args()


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(command)
    print(f"+ {printable}")

    process_env = None

    if env is not None:
        process_env = os.environ.copy()
        process_env.update(env)

    result = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=capture_output,
        text=True,
        env=process_env,
    )

    if check and result.returncode != 0:
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""

        details = "\n".join(
            part for part in (stdout, stderr) if part
        )

        if details:
            raise BootstrapError(
                f"Command failed ({result.returncode}): {printable}\n{details}"
            )

        raise BootstrapError(
            f"Command failed ({result.returncode}): {printable}"
        )

    return result


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise BootstrapError(
            f"Required command '{name}' was not found in PATH."
        )


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BootstrapError(
            f"Unable to read JSON file '{path}': {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise BootstrapError(
            f"Invalid JSON file '{path}': {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise BootstrapError(
            f"JSON file '{path}' must contain an object."
        )

    return data


def write_text_file(
    path: Path,
    content: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )


def verify_project_structure(
    project_dir: Path,
) -> tuple[Path, Path, Path | None]:
    """
    Validate the minimum APF customer repository structure.

    New customer repositories generated by customer-init contain
    .foundation/discovery.yaml and generated.auto.tfvars.json.

    Existing APF reference/customer repositories may predate those generated
    artifacts. They remain valid bootstrap targets as long as the authoritative
    config and Terraform roots exist.
    """

    bootstrap_dir = (
        project_dir
        / "levels"
        / "level0"
        / "bootstrap"
    )

    governance_dir = (
        project_dir
        / "levels"
        / "level0"
        / "governance"
    )

    tfvars_path = (
        bootstrap_dir
        / "generated.auto.tfvars.json"
    )

    required_paths = (
        project_dir / "config" / "foundation.yaml",
        project_dir / "config" / "customer.yaml",
        project_dir / "config" / "platform.yaml",
        bootstrap_dir / "versions.tf",
        bootstrap_dir / "providers.tf",
        bootstrap_dir / "variables.tf",
        bootstrap_dir / "main.tf",
        bootstrap_dir / "outputs.tf",
        governance_dir / "backend.tf",
        governance_dir / "versions.tf",
        governance_dir / "providers.tf",
        governance_dir / "variables.tf",
        governance_dir / "main.tf",
        governance_dir / "outputs.tf",
    )

    missing = [
        str(path.relative_to(project_dir))
        for path in required_paths
        if not path.is_file()
    ]

    if missing:
        formatted = "\n".join(
            f"  - {path}" for path in missing
        )

        raise BootstrapError(
            "The project does not look like an APF customer repository. "
            f"Missing files:\n{formatted}"
        )

    discovery_path = (
        project_dir
        / ".foundation"
        / "discovery.yaml"
    )

    if not discovery_path.is_file():
        print(
            "[INFO] .foundation/discovery.yaml is not present. "
            "Treating this as a pre-generator/legacy APF customer repository."
        )

    if not tfvars_path.is_file():
        print(
            "[INFO] generated.auto.tfvars.json is not present. "
            "Customer-bootstrap will read Azure context from config/customer.yaml."
        )
        return (
            bootstrap_dir,
            governance_dir,
            None,
        )

    return (
        bootstrap_dir,
        governance_dir,
        tfvars_path,
    )


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = yaml.safe_load(handle)
    except OSError as exc:
        raise BootstrapError(
            f"Unable to read YAML file '{path}': {exc}"
        ) from exc
    except yaml.YAMLError as exc:
        raise BootstrapError(
            f"Invalid YAML file '{path}': {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise BootstrapError(
            f"YAML file '{path}' must contain an object."
        )

    return data


def load_azure_context(
    *,
    project_dir: Path,
    generated_tfvars_path: Path | None,
) -> tuple[str, str]:
    """
    Resolve tenant/subscription from generated inputs when available.

    Older APF customer repositories can fall back to config/customer.yaml.
    This makes customer-bootstrap usable for the existing APF reference
    environment without pretending that it was generated by customer-init.
    """

    if generated_tfvars_path is not None:
        tfvars = load_json(
            generated_tfvars_path
        )

        tenant_id = str(
            tfvars.get("tenant_id", "")
        )

        subscription_id = str(
            tfvars.get("subscription_id", "")
        )

        if tenant_id and subscription_id:
            print(
                "[PASS] Azure context loaded from generated.auto.tfvars.json."
            )
            return (
                tenant_id,
                subscription_id,
            )

        raise BootstrapError(
            "generated.auto.tfvars.json exists but does not contain both "
            "tenant_id and subscription_id."
        )

    customer_config = load_yaml(
        project_dir
        / "config"
        / "customer.yaml"
    )

    try:
        azure = customer_config["azure"]
        tenant_id = str(
            azure["tenant_id"]
        )
        subscription_id = str(
            azure["bootstrap_subscription_id"]
        )
    except (KeyError, TypeError) as exc:
        raise BootstrapError(
            "config/customer.yaml does not contain the required "
            "azure.tenant_id and azure.bootstrap_subscription_id values."
        ) from exc

    if not tenant_id or not subscription_id:
        raise BootstrapError(
            "config/customer.yaml contains empty Azure tenant/subscription IDs."
        )

    print(
        "[PASS] Azure context loaded from config/customer.yaml "
        "(legacy compatibility mode)."
    )

    return (
        tenant_id,
        subscription_id,
    )


def verify_terraform_version() -> None:
    result = run_command(
        ["terraform", "version"],
        capture_output=True,
    )

    first_line = (
        result.stdout.splitlines()[0].strip()
        if result.stdout
        else ""
    )

    if not first_line.startswith(
        TERRAFORM_REQUIRED_VERSION_PREFIX
    ):
        raise BootstrapError(
            "APF currently requires Terraform 1.17.x. "
            f"Detected: {first_line or 'unknown'}"
        )

    print(f"[PASS] {first_line}")


def get_azure_account() -> dict[str, Any]:
    result = run_command(
        [
            "az",
            "account",
            "show",
            "--output",
            "json",
        ],
        capture_output=True,
    )

    try:
        account = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BootstrapError(
            "Azure CLI returned invalid account JSON."
        ) from exc

    if not isinstance(account, dict):
        raise BootstrapError(
            "Azure CLI returned an unexpected account response."
        )

    return account


def configure_azure_context(
    expected_tenant_id: str,
    expected_subscription_id: str,
) -> None:
    account = get_azure_account()

    current_tenant = str(
        account.get("tenantId", "")
    )

    if current_tenant.lower() != expected_tenant_id.lower():
        raise BootstrapError(
            "The active Azure CLI tenant does not match the generated "
            "customer configuration.\n"
            f"Expected tenant: {expected_tenant_id}\n"
            f"Current tenant:  {current_tenant or 'unknown'}"
        )

    current_subscription = str(
        account.get("id", "")
    )

    if (
        current_subscription.lower()
        != expected_subscription_id.lower()
    ):
        print(
            "Switching Azure CLI to the configured bootstrap "
            f"subscription {expected_subscription_id}..."
        )

        run_command(
            [
                "az",
                "account",
                "set",
                "--subscription",
                expected_subscription_id,
            ]
        )

        account = get_azure_account()

        current_subscription = str(
            account.get("id", "")
        )

        if (
            current_subscription.lower()
            != expected_subscription_id.lower()
        ):
            raise BootstrapError(
                "Unable to activate the configured bootstrap subscription."
            )

    print(
        "[PASS] Azure CLI tenant and subscription match "
        "the generated APF configuration."
    )


def backend_state_mode(
    bootstrap_dir: Path,
) -> str:
    backend_tf = bootstrap_dir / "backend.tf"
    backend_hcl = bootstrap_dir / "backend.hcl"

    has_tf = backend_tf.is_file()
    has_hcl = backend_hcl.is_file()

    if has_tf and has_hcl:
        return "remote"

    if not has_tf and not has_hcl:
        return "local"

    raise BootstrapError(
        "Incomplete bootstrap backend configuration detected. "
        "Expected either both backend.tf and backend.hcl or neither."
    )


def terraform_init_bootstrap(
    bootstrap_dir: Path,
    state_mode: str,
) -> None:
    if state_mode == "remote":
        run_command(
            [
                "terraform",
                "init",
                "-reconfigure",
                "-backend-config=backend.hcl",
            ],
            cwd=bootstrap_dir,
        )
        return

    run_command(
        [
            "terraform",
            "init",
        ],
        cwd=bootstrap_dir,
    )


def terraform_validate(
    bootstrap_dir: Path,
) -> None:
    run_command(
        [
            "terraform",
            "fmt",
            "-check",
            "-recursive",
        ],
        cwd=bootstrap_dir,
    )

    run_command(
        [
            "terraform",
            "validate",
        ],
        cwd=bootstrap_dir,
    )


def terraform_plan(
    bootstrap_dir: Path,
) -> Path:
    plan_path = (
        bootstrap_dir
        / ".apf-bootstrap.tfplan"
    )

    if plan_path.exists():
        plan_path.unlink()

    run_command(
        [
            "terraform",
            "plan",
            "-lock-timeout=5m",
            "-out=.apf-bootstrap.tfplan",
        ],
        cwd=bootstrap_dir,
    )

    return plan_path


def terraform_apply(
    bootstrap_dir: Path,
    plan_path: Path,
) -> None:
    run_command(
        [
            "terraform",
            "apply",
            "-auto-approve",
            plan_path.name,
        ],
        cwd=bootstrap_dir,
    )


def terraform_outputs(
    bootstrap_dir: Path,
) -> dict[str, Any]:
    result = run_command(
        [
            "terraform",
            "output",
            "-json",
        ],
        cwd=bootstrap_dir,
        capture_output=True,
    )

    try:
        outputs = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BootstrapError(
            "Terraform returned invalid output JSON."
        ) from exc

    if not isinstance(outputs, dict):
        raise BootstrapError(
            "Terraform returned an unexpected output structure."
        )

    return outputs


def output_value(
    outputs: dict[str, Any],
    name: str,
) -> Any:
    entry = outputs.get(name)

    if not isinstance(entry, dict):
        return None

    return entry.get("value")


def require_output_value(
    outputs: dict[str, Any],
    name: str,
) -> Any:
    value = output_value(
        outputs,
        name,
    )

    if value in (None, ""):
        raise BootstrapError(
            f"Required Terraform output '{name}' is missing."
        )

    return value


def first_nonempty(
    *values: Any,
) -> Any:
    for value in values:
        if value not in (None, ""):
            return value

    return None


def extract_backend_configuration(
    outputs: dict[str, Any],
    *,
    tenant_id: str,
    subscription_id: str,
) -> dict[str, str]:
    backend = output_value(
        outputs,
        "backend_configuration",
    )

    if backend is None:
        backend = {}

    if not isinstance(backend, dict):
        raise BootstrapError(
            "Terraform output 'backend_configuration' must be an object."
        )

    resource_group_name = first_nonempty(
        backend.get("resource_group_name"),
        output_value(
            outputs,
            "resource_group_name",
        ),
        output_value(
            outputs,
            "bootstrap_resource_group_name",
        ),
    )

    storage_account_name = first_nonempty(
        backend.get("storage_account_name"),
        output_value(
            outputs,
            "storage_account_name",
        ),
        output_value(
            outputs,
            "state_storage_account_name",
        ),
    )

    container_name = first_nonempty(
        backend.get("container_name"),
        backend.get("storage_container_name"),
        output_value(
            outputs,
            "container_name",
        ),
        output_value(
            outputs,
            "state_container_name",
        ),
    )

    missing = [
        name
        for name, value in (
            (
                "resource_group_name",
                resource_group_name,
            ),
            (
                "storage_account_name",
                storage_account_name,
            ),
            (
                "container_name",
                container_name,
            ),
        )
        if not value
    ]

    if missing:
        raise BootstrapError(
            "Unable to derive AzureRM backend configuration from "
            "Terraform outputs. Missing: "
            + ", ".join(missing)
        )

    return {
        "tenant_id": tenant_id,
        "subscription_id": subscription_id,
        "resource_group_name": str(resource_group_name),
        "storage_account_name": str(storage_account_name),
        "container_name": str(container_name),
    }


def hcl_string(value: str) -> str:
    return json.dumps(value)


def build_backend_hcl(
    backend: dict[str, str],
    *,
    state_key: str,
) -> str:
    lines = [
        "# Generated by Azure Platform Foundation customer-bootstrap.",
        "# Do not edit manually.",
        "",
        (
            "tenant_id            = "
            f"{hcl_string(backend['tenant_id'])}"
        ),
        (
            "subscription_id      = "
            f"{hcl_string(backend['subscription_id'])}"
        ),
        (
            "resource_group_name  = "
            f"{hcl_string(backend['resource_group_name'])}"
        ),
        (
            "storage_account_name = "
            f"{hcl_string(backend['storage_account_name'])}"
        ),
        (
            "container_name       = "
            f"{hcl_string(backend['container_name'])}"
        ),
        (
            "key                  = "
            f"{hcl_string(state_key)}"
        ),
        "use_azuread_auth     = true",
        "use_cli              = true",
        "",
    ]

    return "\n".join(lines)


def write_backend_files(
    bootstrap_dir: Path,
    governance_dir: Path,
    backend: dict[str, str],
) -> None:
    bootstrap_backend_tf = (
        bootstrap_dir
        / "backend.tf"
    )

    if (
        bootstrap_backend_tf.exists()
        and bootstrap_backend_tf.read_text(
            encoding="utf-8"
        ) != BOOTSTRAP_BACKEND_TF
    ):
        raise BootstrapError(
            "bootstrap/backend.tf already exists with unexpected content. "
            "Refusing to overwrite it."
        )

    write_text_file(
        bootstrap_backend_tf,
        BOOTSTRAP_BACKEND_TF,
    )

    write_text_file(
        bootstrap_dir / "backend.hcl",
        build_backend_hcl(
            backend,
            state_key=BOOTSTRAP_STATE_KEY,
        ),
    )

    write_text_file(
        governance_dir / "backend.hcl",
        build_backend_hcl(
            backend,
            state_key=GOVERNANCE_STATE_KEY,
        ),
    )

    print(
        "[PASS] Generated bootstrap backend.tf/backend.hcl "
        "and governance backend.hcl."
    )


def get_signed_in_user_object_id() -> str:
    result = run_command(
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
        raise BootstrapError(
            "Unable to determine the signed-in Azure user object ID."
        )

    return object_id


def find_state_role_assignment(
    *,
    principal_id: str,
    scope: str,
) -> str | None:
    result = run_command(
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
            (
                "[?roleDefinitionName=='"
                + STATE_DATA_ROLE
                + "'].id | [0]"
            ),
            "--output",
            "tsv",
        ],
        capture_output=True,
    )

    assignment_id = result.stdout.strip()

    return assignment_id or None


def ensure_temporary_state_access(
    *,
    principal_id: str,
    scope: str,
) -> str | None:
    existing = find_state_role_assignment(
        principal_id=principal_id,
        scope=scope,
    )

    if existing:
        print(
            "[PASS] Signed-in bootstrap user already has "
            f"{STATE_DATA_ROLE} on the state container."
        )
        return None

    print(
        "Granting temporary state-container access to the "
        "signed-in bootstrap user..."
    )

    result = run_command(
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
        raise BootstrapError(
            "Azure CLI did not return the temporary role assignment ID."
        )

    print(
        "[PASS] Temporary state-container access granted."
    )

    return assignment_id


def remove_role_assignment(
    assignment_id: str,
) -> None:
    print(
        "Removing temporary bootstrap state-container access..."
    )

    run_command(
        [
            "az",
            "role",
            "assignment",
            "delete",
            "--ids",
            assignment_id,
        ]
    )

    print(
        "[PASS] Temporary state-container access removed."
    )


def migrate_bootstrap_state(
    bootstrap_dir: Path,
) -> None:
    commands = [
        [
            "terraform",
            "init",
            "-migrate-state",
            "-force-copy",
            "-backend-config=backend.hcl",
        ],
        [
            "terraform",
            "init",
            "-reconfigure",
            "-backend-config=backend.hcl",
        ],
    ]

    last_error: BootstrapError | None = None

    for attempt in range(1, 7):
        command = commands[0] if attempt == 1 else commands[1]

        try:
            run_command(
                command,
                cwd=bootstrap_dir,
            )
            return
        except BootstrapError as exc:
            last_error = exc

            if attempt == 6:
                break

            print(
                "Backend initialization is not ready yet; retrying..."
            )
            time.sleep(5)

    assert last_error is not None
    raise last_error


def verify_remote_state(
    bootstrap_dir: Path,
) -> None:
    result = run_command(
        [
            "terraform",
            "state",
            "list",
        ],
        cwd=bootstrap_dir,
        capture_output=True,
    )

    resources = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    if not resources:
        raise BootstrapError(
            "Remote Terraform state is readable but contains no resources."
        )

    print(
        f"[PASS] Remote bootstrap state is readable "
        f"({len(resources)} resources)."
    )


def ensure_governance_backend(
    governance_dir: Path,
    backend: dict[str, str],
    *,
    allow_create: bool,
) -> None:
    backend_hcl = (
        governance_dir
        / "backend.hcl"
    )

    if backend_hcl.is_file():
        print(
            "[PASS] Existing governance backend.hcl will be preserved."
        )
        return

    if not allow_create:
        raise BootstrapError(
            "Governance backend.hcl does not exist yet. "
            "Run customer-bootstrap with --governance --apply after the "
            "bootstrap backend exists so APF can generate it."
        )

    write_text_file(
        backend_hcl,
        build_backend_hcl(
            backend,
            state_key=GOVERNANCE_STATE_KEY,
        ),
    )

    print(
        "[PASS] Generated governance backend.hcl."
    )


def governance_tf_environment(
    *,
    tenant_id: str,
    subscription_id: str,
    outputs: dict[str, Any],
) -> dict[str, str]:
    governance_principal_id = str(
        require_output_value(
            outputs,
            "governance_identity_principal_id",
        )
    )

    state_container_id = str(
        require_output_value(
            outputs,
            "state_container_id",
        )
    )

    return {
        "TF_VAR_tenant_id": tenant_id,
        "TF_VAR_subscription_id": subscription_id,
        "TF_VAR_governance_principal_id": governance_principal_id,
        "TF_VAR_state_container_id": state_container_id,
    }


def terraform_init_governance(
    governance_dir: Path,
) -> None:
    run_command(
        [
            "terraform",
            "init",
            "-reconfigure",
            "-backend-config=backend.hcl",
        ],
        cwd=governance_dir,
    )


def terraform_validate_governance(
    governance_dir: Path,
    governance_env: dict[str, str],
) -> None:
    run_command(
        [
            "terraform",
            "fmt",
            "-check",
            "-recursive",
        ],
        cwd=governance_dir,
        env=governance_env,
    )

    run_command(
        [
            "terraform",
            "validate",
        ],
        cwd=governance_dir,
        env=governance_env,
    )


def terraform_plan_governance(
    governance_dir: Path,
    governance_env: dict[str, str],
) -> Path:
    plan_path = (
        governance_dir
        / ".apf-governance.tfplan"
    )

    if plan_path.exists():
        plan_path.unlink()

    run_command(
        [
            "terraform",
            "plan",
            "-lock-timeout=5m",
            "-out=.apf-governance.tfplan",
        ],
        cwd=governance_dir,
        env=governance_env,
    )

    return plan_path


def terraform_apply_governance(
    governance_dir: Path,
    plan_path: Path,
    governance_env: dict[str, str],
) -> None:
    run_command(
        [
            "terraform",
            "apply",
            "-auto-approve",
            plan_path.name,
        ],
        cwd=governance_dir,
        env=governance_env,
    )


def verify_governance_state(
    governance_dir: Path,
    governance_env: dict[str, str],
) -> None:
    result = run_command(
        [
            "terraform",
            "state",
            "list",
        ],
        cwd=governance_dir,
        capture_output=True,
        env=governance_env,
    )

    resources = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    if not resources:
        raise BootstrapError(
            "Governance Terraform state is readable but contains no resources."
        )

    print(
        f"[PASS] Governance remote state is readable "
        f"({len(resources)} resources)."
    )


def cleanup_plan(
    plan_path: Path,
) -> None:
    if plan_path.exists():
        plan_path.unlink()


def main() -> int:
    args = parse_arguments()

    project_dir = args.project_dir.resolve()

    print(
        "Azure Platform Foundation customer bootstrap"
    )
    print(
        "--------------------------------------------"
    )
    print(f"Project: {project_dir}")
    print()

    try:
        require_command("terraform")
        require_command("az")

        (
            bootstrap_dir,
            governance_dir,
            tfvars_path,
        ) = verify_project_structure(
            project_dir
        )

        (
            tenant_id,
            subscription_id,
        ) = load_azure_context(
            project_dir=project_dir,
            generated_tfvars_path=tfvars_path,
        )

        print("Preflight checks...")
        verify_terraform_version()

        configure_azure_context(
            expected_tenant_id=tenant_id,
            expected_subscription_id=subscription_id,
        )

        state_mode = backend_state_mode(
            bootstrap_dir
        )

        if state_mode == "local":
            print(
                "[INFO] Bootstrap currently uses local Terraform state."
            )
        else:
            print(
                "[INFO] Bootstrap already uses the AzureRM remote backend."
            )

        print()
        print("Initializing Level 0 bootstrap...")
        terraform_init_bootstrap(
            bootstrap_dir,
            state_mode,
        )

        print()
        print("Validating Level 0 bootstrap...")
        terraform_validate(
            bootstrap_dir
        )

        print()
        print("Planning Level 0 bootstrap...")
        plan_path = terraform_plan(
            bootstrap_dir
        )

        if not args.apply:
            cleanup_plan(
                plan_path
            )

            print()
            print(
                "Bootstrap plan completed successfully."
            )
            print(
                "No bootstrap Azure changes were applied."
            )

            if not args.governance:
                print(
                    "Run the same command with --apply to execute "
                    "the bootstrap lifecycle."
                )
                return 0

            print(
                "Continuing with a governance plan against the "
                "current bootstrap state."
            )

        else:
            print()
            print("Applying Level 0 bootstrap...")
            terraform_apply(
                bootstrap_dir,
                plan_path,
            )

            cleanup_plan(
                plan_path
            )

        print()
        print("Reading Level 0 bootstrap outputs...")
        outputs = terraform_outputs(
            bootstrap_dir
        )

        backend = extract_backend_configuration(
            outputs,
            tenant_id=tenant_id,
            subscription_id=subscription_id,
        )

        state_container_id = str(
            require_output_value(
                outputs,
                "state_container_id",
            )
        )

        if args.apply:
            if state_mode == "remote":
                print()
                print(
                    "[INFO] Bootstrap state was already remote. "
                    "Existing backend files will be preserved."
                )

                terraform_init_bootstrap(
                    bootstrap_dir,
                    "remote",
                )

                verify_remote_state(
                    bootstrap_dir
                )

            else:
                write_backend_files(
                    bootstrap_dir=bootstrap_dir,
                    governance_dir=governance_dir,
                    backend=backend,
                )

                principal_id = get_signed_in_user_object_id()

                temporary_assignment_id: str | None = None

                try:
                    temporary_assignment_id = (
                        ensure_temporary_state_access(
                            principal_id=principal_id,
                            scope=state_container_id,
                        )
                    )

                    print()
                    print(
                        "Migrating Level 0 bootstrap state to Azure..."
                    )

                    migrate_bootstrap_state(
                        bootstrap_dir
                    )

                    print()
                    print(
                        "Verifying migrated remote state..."
                    )

                    verify_remote_state(
                        bootstrap_dir
                    )

                finally:
                    if (
                        temporary_assignment_id
                        and not args.keep_temporary_state_access
                    ):
                        remove_role_assignment(
                            temporary_assignment_id
                        )

        if not args.governance:
            print()
            print(
                "Level 0 bootstrap lifecycle completed successfully."
            )

            if args.apply:
                print(
                    f"Bootstrap state:  {BOOTSTRAP_STATE_KEY}"
                )
                print(
                    f"Governance state: {GOVERNANCE_STATE_KEY}"
                )

            print()
            print(
                "Use --governance to include the Level 0 governance "
                "handover."
            )
            return 0

        print()
        print("Preparing Level 0 governance handover...")

        ensure_governance_backend(
            governance_dir,
            backend,
            allow_create=args.apply,
        )

        governance_env = governance_tf_environment(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            outputs=outputs,
        )

        print(
            "[PASS] Governance Terraform inputs derived from "
            "bootstrap outputs."
        )

        print()
        print("Initializing Level 0 governance...")
        terraform_init_governance(
            governance_dir
        )

        print()
        print("Validating Level 0 governance...")
        terraform_validate_governance(
            governance_dir,
            governance_env,
        )

        print()
        print("Planning Level 0 governance...")
        governance_plan_path = terraform_plan_governance(
            governance_dir,
            governance_env,
        )

        if not args.apply:
            cleanup_plan(
                governance_plan_path
            )

            print()
            print(
                "Governance plan completed successfully."
            )
            print(
                "No governance Azure changes were applied."
            )
            print()
            print(
                "Run with --governance --apply to execute both "
                "the bootstrap and governance lifecycle stages."
            )
            return 0

        print()
        print("Applying Level 0 governance...")
        terraform_apply_governance(
            governance_dir,
            governance_plan_path,
            governance_env,
        )

        cleanup_plan(
            governance_plan_path
        )

        print()
        print("Verifying Level 0 governance state...")
        verify_governance_state(
            governance_dir,
            governance_env,
        )

        print()
        print(
            "Level 0 bootstrap and governance lifecycle "
            "completed successfully."
        )
        print(
            f"Bootstrap state:  {BOOTSTRAP_STATE_KEY}"
        )
        print(
            f"Governance state: {GOVERNANCE_STATE_KEY}"
        )

        return 0

    except BootstrapError as exc:
        print()
        print(
            f"[ERROR] {exc}",
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print()
        print(
            "[ERROR] Bootstrap interrupted.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
