#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


TERRAFORM_VERSION = "1.17.1"
TERRAFORM_REQUIRED_VERSION = "~> 1.17"
AZURERM_VERSION = "4.81.0"
STATE_KEY = "level1.management-groups.tfstate"
MODULE_CONTRACT = "commit18"


class ConfigureError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the APF Level 1 management-group Terraform root "
            "and GitHub workflows in an existing customer repository."
        )
    )
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write files. Without this flag the command is dry-run only.",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigureError(f"Unable to read YAML '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigureError(f"YAML '{path}' must contain an object.")
    return data


def require_project(
    project_dir: Path,
) -> tuple[dict, dict, dict, dict]:
    paths = {
        "foundation": project_dir / "config/foundation.yaml",
        "customer": project_dir / "config/customer.yaml",
        "platform": project_dir / "config/platform.yaml",
        "bootstrap": project_dir / ".foundation/level0-bootstrap.yaml",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise ConfigureError(
            "Missing required APF customer files:\n  - "
            + "\n  - ".join(missing)
        )
    return (
        load_yaml(paths["foundation"]),
        load_yaml(paths["customer"]),
        load_yaml(paths["platform"]),
        load_yaml(paths["bootstrap"]),
    )


def management_subscription_id(customer: dict[str, Any]) -> str:
    azure = customer.get("azure") or {}
    value = (
        azure.get("management_subscription_id")
        or azure.get("bootstrap_subscription_id")
    )
    if not value:
        raise ConfigureError(
            "Azure management/bootstrap subscription ID is required."
        )
    return str(value)


def validate_inputs(
    foundation: dict[str, Any],
    customer: dict[str, Any],
    platform: dict[str, Any],
    bootstrap: dict[str, Any],
) -> None:
    try:
        if platform["execution"]["provider"] != "github":
            raise ConfigureError(
                "Level 1 generation supports GitHub execution only."
            )

        if bootstrap["azure"]["tenant_id"] != customer["azure"]["tenant_id"]:
            raise ConfigureError(
                "Level 0 bootstrap tenant does not match customer.yaml."
            )

        if (
            bootstrap["azure"]["subscription_id"]
            != customer["azure"]["bootstrap_subscription_id"]
        ):
            raise ConfigureError(
                "Level 0 bootstrap subscription does not match customer.yaml."
            )

        backend = bootstrap["bootstrap"]["backend_configuration"]
        for key in (
            "resource_group_name",
            "storage_account_name",
            "container_name",
        ):
            if not backend.get(key):
                raise ConfigureError(
                    f"Level 0 backend configuration is missing '{key}'."
                )

        if not foundation["foundation"]["version"]:
            raise ConfigureError("foundation.version is required.")

        management_subscription_id(customer)

    except KeyError as exc:
        raise ConfigureError(
            f"Required APF configuration field is missing: {exc}"
        ) from exc


def hcl_string(value: str) -> str:
    return json.dumps(value)


def render_versions() -> str:
    return f'''terraform {{
  required_version = "{TERRAFORM_REQUIRED_VERSION}"

  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "{AZURERM_VERSION}"
    }}
  }}
}}
'''


def render_provider() -> str:
    return '''provider "azurerm" {
  features {}

  tenant_id       = var.tenant_id
  subscription_id = var.subscription_id

  storage_use_azuread = true
}
'''


def render_variables() -> str:
    return '''variable "tenant_id" {
  description = "Azure tenant ID."
  type        = string
}

variable "subscription_id" {
  description = "APF bootstrap subscription ID."
  type        = string
}

variable "management_subscription_id" {
  description = "APF Management platform subscription ID."
  type        = string
}

variable "name_prefix" {
  description = "APF management-group root ID and prefix."
  type        = string
}

variable "root_display_name" {
  description = "Display name for the APF root management group."
  type        = string
}

variable "bootstrap_resource_group_name" {
  description = "Level 0 bootstrap resource group containing APF identities."
  type        = string
}
'''


def render_main(foundation_ref: str) -> str:
    return f'''# APF module contract: {MODULE_CONTRACT}

data "azurerm_user_assigned_identity" "plan" {{
  name                = "${{var.name_prefix}}-id-l0-plan"
  resource_group_name = var.bootstrap_resource_group_name
}}

data "azurerm_user_assigned_identity" "governance" {{
  name                = "${{var.name_prefix}}-id-l0-governance"
  resource_group_name = var.bootstrap_resource_group_name
}}

module "management_groups" {{
  source = "git::https://github.com/meipenlei/azure-platform-foundation.git//foundation/modules/level1-management-groups?ref={foundation_ref}"

  tenant_id                  = var.tenant_id
  bootstrap_subscription_id  = var.subscription_id
  management_subscription_id = var.management_subscription_id
  name_prefix                = var.name_prefix
  root_display_name          = var.root_display_name
  plan_principal_id          = data.azurerm_user_assigned_identity.plan.principal_id
  governance_principal_id    = data.azurerm_user_assigned_identity.governance.principal_id
}}
'''


def render_outputs() -> str:
    return '''output "root_management_group_id" {
  value = module.management_groups.root_management_group_id
}

output "root_management_group_name" {
  value = module.management_groups.root_management_group_name
}

output "management_group_ids" {
  value = module.management_groups.management_group_ids
}

output "bootstrap_subscription_parent_management_group_id" {
  value = module.management_groups.bootstrap_subscription_parent_management_group_id
}

output "management_subscription_id" {
  value = module.management_groups.management_subscription_id
}

output "policy_deployment_root_scope" {
  value = module.management_groups.policy_deployment_root_scope
}
'''


def render_backend_tf() -> str:
    return '''terraform {
  backend "azurerm" {}
}
'''


def render_backend_hcl(
    *,
    tenant_id: str,
    subscription_id: str,
    backend: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Generated by Azure Platform Foundation customer-level1.",
            "# Do not edit manually.",
            "",
            f"tenant_id            = {hcl_string(tenant_id)}",
            f"subscription_id      = {hcl_string(subscription_id)}",
            (
                "resource_group_name  = "
                f"{hcl_string(str(backend['resource_group_name']))}"
            ),
            (
                "storage_account_name = "
                f"{hcl_string(str(backend['storage_account_name']))}"
            ),
            (
                "container_name       = "
                f"{hcl_string(str(backend['container_name']))}"
            ),
            f"key                  = {hcl_string(STATE_KEY)}",
            "use_azuread_auth     = true",
            "use_cli              = true",
            "",
        ]
    )


def render_tfvars(
    *,
    customer: dict[str, Any],
    platform: dict[str, Any],
    bootstrap: dict[str, Any],
) -> str:
    values = {
        "tenant_id": customer["azure"]["tenant_id"],
        "subscription_id": customer["azure"]["bootstrap_subscription_id"],
        "management_subscription_id": management_subscription_id(customer),
        "name_prefix": platform["naming"]["prefix"],
        "root_display_name": (
            f"{customer['customer']['display_name']} Platform"
        ),
        "bootstrap_resource_group_name": bootstrap["bootstrap"][
            "resource_group_name"
        ],
    }
    return json.dumps(values, indent=2) + "\n"


def render_plan_workflow() -> str:
    return f'''name: Terraform Plan - Level 1 Management Groups

on:
  pull_request:
    paths:
      - "levels/level1/management-groups/**"
      - ".github/workflows/terraform-level1-management-groups-plan.yml"

permissions:
  contents: read
  id-token: write

env:
  TF_IN_AUTOMATION: "true"
  TF_INPUT: "false"
  AZURE_CORE_OUTPUT: "none"

jobs:
  level1-plan:
    name: Level 1 Management Groups Plan
    runs-on: ubuntu-24.04

    steps:
      - name: Checkout repository
        uses: actions/checkout@v7

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: "{TERRAFORM_VERSION}"

      - name: Azure login with Plan identity
        uses: azure/login@v3
        with:
          client-id: ${{{{ vars.AZURE_PLAN_CLIENT_ID }}}}
          tenant-id: ${{{{ vars.AZURE_TENANT_ID }}}}
          subscription-id: ${{{{ vars.AZURE_SUBSCRIPTION_ID }}}}

      - name: Wait for Level 1 reader delegation
        shell: bash
        run: |
          root_id="$(jq -r '.name_prefix' levels/level1/management-groups/generated.auto.tfvars.json)"

          for attempt in {{1..60}}; do
            if az rest \
              --method get \
              --url "https://management.azure.com/providers/Microsoft.Management/managementGroups/$root_id?api-version=2020-05-01" \
              --only-show-errors \
              --output none 2>/dev/null; then
              echo "[PASS] Level 1 reader delegation is effective."
              exit 0
            fi

            echo "Level 1 reader delegation is not effective yet; retrying..."
            sleep 10
          done

          echo "[ERROR] Level 1 reader delegation did not become effective within 10 minutes." >&2
          exit 1

      - name: Initialize Terraform
        working-directory: levels/level1/management-groups
        run: |
          terraform init \
            -upgrade \
            -reconfigure \
            -backend-config=backend.hcl \
            -backend-config="use_cli=true"

      - name: Terraform format check
        working-directory: levels/level1/management-groups
        run: terraform fmt -check -recursive

      - name: Terraform validate
        working-directory: levels/level1/management-groups
        run: terraform validate

      - name: Terraform plan
        working-directory: levels/level1/management-groups
        run: terraform plan -lock-timeout=5m -no-color
'''


def render_apply_workflow() -> str:
    return f'''name: Terraform Apply - Level 1 Management Groups

on:
  workflow_dispatch:

permissions:
  contents: read
  id-token: write

env:
  TF_IN_AUTOMATION: "true"
  TF_INPUT: "false"
  AZURE_CORE_OUTPUT: "none"

jobs:
  level1-apply:
    name: Level 1 Management Groups Apply
    runs-on: ubuntu-24.04

    environment:
      name: apf-governance

    steps:
      - name: Checkout repository
        uses: actions/checkout@v7

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: "{TERRAFORM_VERSION}"

      - name: Azure login with Governance identity
        uses: azure/login@v3
        with:
          client-id: ${{{{ vars.AZURE_GOVERNANCE_CLIENT_ID }}}}
          tenant-id: ${{{{ vars.AZURE_TENANT_ID }}}}
          subscription-id: ${{{{ vars.AZURE_SUBSCRIPTION_ID }}}}

      - name: Wait for Level 1 governance delegation
        shell: bash
        run: |
          root_id="$(jq -r '.name_prefix' levels/level1/management-groups/generated.auto.tfvars.json)"

          for attempt in {{1..60}}; do
            if az rest \
              --method get \
              --url "https://management.azure.com/providers/Microsoft.Management/managementGroups/$root_id?api-version=2020-05-01" \
              --only-show-errors \
              --output none 2>/dev/null; then
              echo "[PASS] Level 1 governance delegation is effective."
              exit 0
            fi

            echo "Level 1 governance delegation is not effective yet; retrying..."
            sleep 10
          done

          echo "[ERROR] Level 1 governance delegation did not become effective within 10 minutes." >&2
          exit 1

      - name: Initialize Terraform
        working-directory: levels/level1/management-groups
        run: |
          terraform init \
            -upgrade \
            -reconfigure \
            -backend-config=backend.hcl \
            -backend-config="use_cli=true"

      - name: Terraform format check
        working-directory: levels/level1/management-groups
        run: terraform fmt -check -recursive

      - name: Terraform validate
        working-directory: levels/level1/management-groups
        run: terraform validate

      - name: Terraform plan
        working-directory: levels/level1/management-groups
        run: terraform plan -lock-timeout=5m -out=level1-management-groups.tfplan

      - name: Terraform apply
        working-directory: levels/level1/management-groups
        run: terraform apply -auto-approve level1-management-groups.tfplan
'''


def desired_files(
    *,
    project_dir: Path,
    foundation: dict[str, Any],
    customer: dict[str, Any],
    platform: dict[str, Any],
    bootstrap: dict[str, Any],
) -> dict[Path, str]:
    target = project_dir / "levels/level1/management-groups"
    backend = bootstrap["bootstrap"]["backend_configuration"]
    foundation_ref = str(foundation["foundation"]["version"])

    return {
        target / "versions.tf": render_versions(),
        target / "providers.tf": render_provider(),
        target / "variables.tf": render_variables(),
        target / "main.tf": render_main(foundation_ref),
        target / "outputs.tf": render_outputs(),
        target / "backend.tf": render_backend_tf(),
        target / "backend.hcl": render_backend_hcl(
            tenant_id=customer["azure"]["tenant_id"],
            subscription_id=customer["azure"]["bootstrap_subscription_id"],
            backend=backend,
        ),
        target / "generated.auto.tfvars.json": render_tfvars(
            customer=customer,
            platform=platform,
            bootstrap=bootstrap,
        ),
        project_dir
        / ".github/workflows/terraform-level1-management-groups-plan.yml": render_plan_workflow(),
        project_dir
        / ".github/workflows/terraform-level1-management-groups-apply.yml": render_apply_workflow(),
    }


def changed_files(files: dict[Path, str]) -> list[Path]:
    result = []
    for path, content in files.items():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current != content:
            result.append(path)
    return result


def write_files(files: dict[Path, str]) -> None:
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.resolve()

    print("Azure Platform Foundation Level 1 configuration")
    print("-----------------------------------------------")
    print(f"Project: {project_dir}")
    print(f"Mode:    {'apply' if args.apply else 'dry-run'}")
    print()

    try:
        foundation, customer, platform, bootstrap = require_project(
            project_dir
        )
        validate_inputs(
            foundation=foundation,
            customer=customer,
            platform=platform,
            bootstrap=bootstrap,
        )

        files = desired_files(
            project_dir=project_dir,
            foundation=foundation,
            customer=customer,
            platform=platform,
            bootstrap=bootstrap,
        )
        changes = changed_files(files)

        if not changes:
            print(
                "[PASS] Level 1 management-group project is already generated."
            )
            return 0

        print("Planned generated-file changes:")
        for path in changes:
            print(f"  - {path.relative_to(project_dir)}")

        if not args.apply:
            print()
            print("Dry-run only. Re-run with --apply to write these files.")
            return 0

        write_files(files)
        print()
        print("[PASS] Level 1 management-group project generated.")
        print("[PASS] No Azure resources were changed.")
        return 0

    except (ConfigureError, OSError, KeyError, TypeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
