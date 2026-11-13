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
STATE_KEY = "level1.management-platform.tfstate"
LEVEL1_SNAPSHOT = Path(".foundation/level1-management-groups.yaml")
MANAGEMENT_SNAPSHOT = Path(".foundation/level1-management-platform.yaml")
MODULE_CONTRACT = "commit18"


class ConfigureError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the APF Level 1 Management platform Terraform root "
            "and protected GitHub workflows."
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
) -> tuple[dict, dict, dict, dict, dict]:
    paths = {
        "foundation": project_dir / "config/foundation.yaml",
        "customer": project_dir / "config/customer.yaml",
        "platform": project_dir / "config/platform.yaml",
        "bootstrap": project_dir / ".foundation/level0-bootstrap.yaml",
        "level1": project_dir / LEVEL1_SNAPSHOT,
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
        load_yaml(paths["level1"]),
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


def log_retention_days(platform: dict[str, Any]) -> int:
    value = (
        (
            (
                (platform.get("management") or {})
                .get("monitoring", {})
            )
            .get("log_analytics", {})
        )
        .get("retention_days", 30)
    )

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 30
        or value > 730
    ):
        raise ConfigureError(
            "management.monitoring.log_analytics.retention_days "
            "must be an integer from 30 to 730."
        )

    return value


def management_group_id(level1: dict[str, Any]) -> str:
    try:
        value = str(
            level1["management_groups"]["management_group_ids"]["management"]
        )
    except (KeyError, TypeError) as exc:
        raise ConfigureError(
            f"{LEVEL1_SNAPSHOT} does not contain the Management group ID."
        ) from exc

    prefix = "/providers/Microsoft.Management/managementGroups/"
    if not value.startswith(prefix):
        raise ConfigureError(
            f"Invalid Management group ID in {LEVEL1_SNAPSHOT}: {value}"
        )
    return value


def validate_inputs(
    foundation: dict[str, Any],
    customer: dict[str, Any],
    platform: dict[str, Any],
    bootstrap: dict[str, Any],
    level1: dict[str, Any],
) -> None:
    try:
        if platform["execution"]["provider"] != "github":
            raise ConfigureError(
                "Commit 18 Management platform generation supports "
                "GitHub execution only."
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

        if level1.get("source") != "terraform-level1-management-groups":
            raise ConfigureError(
                f"{LEVEL1_SNAPSHOT} is not an APF Level 1 Terraform snapshot."
            )

        management_group_id(level1)
        management_subscription_id(customer)
        log_retention_days(platform)

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

    except KeyError as exc:
        raise ConfigureError(
            f"Required APF configuration field is missing: {exc}"
        ) from exc


def hcl_string(value: str) -> str:
    return json.dumps(value)


def names(prefix: str) -> dict[str, str]:
    return {
        "resource_group": f"{prefix}-rg-l1-management",
        "log_analytics": f"{prefix}-law-l1-platform",
        "monitoring_identity": f"{prefix}-id-l1-monitoring",
    }


def resource_id(
    subscription_id: str,
    resource_group_name: str,
    provider: str,
    resource_type: str,
    resource_name: str,
) -> str:
    return (
        f"/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group_name}"
        f"/providers/{provider}/{resource_type}/{resource_name}"
    )


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
  subscription_id = var.management_subscription_id

  storage_use_azuread = true
}
'''


def render_variables() -> str:
    return '''variable "tenant_id" {
  description = "Azure tenant ID."
  type        = string
}

variable "management_subscription_id" {
  description = "Subscription hosting the APF Level 1 Management platform."
  type        = string
}

variable "name_prefix" {
  description = "Stable APF resource naming prefix."
  type        = string
}

variable "location" {
  description = "Primary Azure region for Management platform resources."
  type        = string
}

variable "log_analytics_retention_days" {
  description = "Default analytics retention for the central Log Analytics workspace."
  type        = number
}
'''


def render_main(foundation_ref: str) -> str:
    return f'''# APF module contract: {MODULE_CONTRACT}

module "management_platform" {{
  source = "git::https://github.com/meipenlei/azure-platform-foundation.git//foundation/modules/level1-management-platform?ref={foundation_ref}"

  name_prefix                  = var.name_prefix
  location                     = var.location
  log_analytics_retention_days = var.log_analytics_retention_days
}}
'''


def render_outputs() -> str:
    return '''output "resource_group_id" {
  value = module.management_platform.resource_group_id
}

output "resource_group_name" {
  value = module.management_platform.resource_group_name
}

output "log_analytics_workspace_id" {
  value = module.management_platform.log_analytics_workspace_id
}

output "log_analytics_workspace_name" {
  value = module.management_platform.log_analytics_workspace_name
}

output "log_analytics_workspace_customer_id" {
  value = module.management_platform.log_analytics_workspace_customer_id
}

output "monitoring_identity_id" {
  value = module.management_platform.monitoring_identity_id
}

output "monitoring_identity_client_id" {
  value = module.management_platform.monitoring_identity_client_id
}

output "monitoring_identity_principal_id" {
  value = module.management_platform.monitoring_identity_principal_id
}
'''


def render_backend_tf() -> str:
    return '''terraform {
  backend "azurerm" {}
}
'''


def render_backend_hcl(
    *,
    customer: dict[str, Any],
    bootstrap: dict[str, Any],
) -> str:
    backend = bootstrap["bootstrap"]["backend_configuration"]
    return "\n".join(
        [
            "# Generated by Azure Platform Foundation "
            "customer-level1-management.",
            "# Terraform state remains in the Level 0 APF backend.",
            "",
            f"tenant_id            = "
            f"{hcl_string(customer['azure']['tenant_id'])}",
            f"subscription_id      = "
            f"{hcl_string(customer['azure']['bootstrap_subscription_id'])}",
            "resource_group_name  = "
            f"{hcl_string(str(backend['resource_group_name']))}",
            "storage_account_name = "
            f"{hcl_string(str(backend['storage_account_name']))}",
            "container_name       = "
            f"{hcl_string(str(backend['container_name']))}",
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
) -> str:
    values = {
        "tenant_id": customer["azure"]["tenant_id"],
        "management_subscription_id": management_subscription_id(customer),
        "name_prefix": platform["naming"]["prefix"],
        "location": customer["azure"]["primary_region"],
        "log_analytics_retention_days": log_retention_days(platform),
    }
    return json.dumps(values, indent=2) + "\n"


def render_snapshot(
    *,
    customer: dict[str, Any],
    platform: dict[str, Any],
    level1: dict[str, Any],
) -> str:
    subscription_id = management_subscription_id(customer)
    resource_names = names(str(platform["naming"]["prefix"]))
    resource_group_name = resource_names["resource_group"]

    data = {
        "schema_version": "0.1",
        "source": "generated-terraform-level1-management-platform",
        "module_contract": MODULE_CONTRACT,
        "azure": {
            "subscription_id": subscription_id,
            "location": customer["azure"]["primary_region"],
        },
        "management_group_id": management_group_id(level1),
        "management": {
            "resource_group": {
                "name": resource_group_name,
                "id": (
                    f"/subscriptions/{subscription_id}"
                    f"/resourceGroups/{resource_group_name}"
                ),
            },
            "log_analytics_workspace": {
                "name": resource_names["log_analytics"],
                "id": resource_id(
                    subscription_id,
                    resource_group_name,
                    "Microsoft.OperationalInsights",
                    "workspaces",
                    resource_names["log_analytics"],
                ),
                "retention_days": log_retention_days(platform),
            },
            "monitoring_identity": {
                "name": resource_names["monitoring_identity"],
                "id": resource_id(
                    subscription_id,
                    resource_group_name,
                    "Microsoft.ManagedIdentity",
                    "userAssignedIdentities",
                    resource_names["monitoring_identity"],
                ),
            },
            "terraform_state_key": STATE_KEY,
        },
    }

    return yaml.safe_dump(data, sort_keys=False)


def render_plan_workflow() -> str:
    return f'''name: Terraform Plan - Level 1 Management Platform

on:
  pull_request:
    paths:
      - "levels/level1/management-platform/**"
      - ".foundation/level1-management-platform.yaml"
      - ".github/workflows/terraform-level1-management-platform-plan.yml"

permissions:
  contents: read
  id-token: write

env:
  TF_IN_AUTOMATION: "true"
  TF_INPUT: "false"
  AZURE_CORE_OUTPUT: "none"

jobs:
  management-platform-plan:
    name: Level 1 Management Platform Plan
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

      - name: Initialize Terraform
        working-directory: levels/level1/management-platform
        run: |
          terraform init \
            -upgrade \
            -reconfigure \
            -backend-config=backend.hcl \
            -backend-config="use_cli=true"

      - name: Terraform format check
        working-directory: levels/level1/management-platform
        run: terraform fmt -check -recursive

      - name: Terraform validate
        working-directory: levels/level1/management-platform
        run: terraform validate

      - name: Terraform plan
        working-directory: levels/level1/management-platform
        run: terraform plan -lock-timeout=5m -no-color
'''


def render_apply_workflow() -> str:
    return f'''name: Terraform Apply - Level 1 Management Platform

on:
  workflow_dispatch:
    inputs:
      confirm_apply:
        description: "Confirm deployment of the Level 1 Management platform from main"
        required: true
        default: false
        type: boolean

permissions:
  contents: read
  id-token: write

env:
  TF_IN_AUTOMATION: "true"
  TF_INPUT: "false"
  AZURE_CORE_OUTPUT: "none"

jobs:
  management-platform-apply:
    name: Level 1 Management Platform Apply
    if: ${{{{ github.ref == 'refs/heads/main' && inputs.confirm_apply == true }}}}
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

      - name: Initialize Terraform
        working-directory: levels/level1/management-platform
        run: |
          terraform init \
            -upgrade \
            -reconfigure \
            -backend-config=backend.hcl \
            -backend-config="use_cli=true"

      - name: Terraform format check
        working-directory: levels/level1/management-platform
        run: terraform fmt -check -recursive

      - name: Terraform validate
        working-directory: levels/level1/management-platform
        run: terraform validate

      - name: Terraform plan
        working-directory: levels/level1/management-platform
        run: |
          terraform plan \
            -lock-timeout=5m \
            -out=level1-management-platform.tfplan

      - name: Terraform apply
        working-directory: levels/level1/management-platform
        run: |
          terraform apply \
            -auto-approve \
            level1-management-platform.tfplan

      - name: Verify Management platform outputs
        working-directory: levels/level1/management-platform
        shell: bash
        run: |
          set -euo pipefail

          terraform output -json > "$RUNNER_TEMP/level1-management-platform.json"

          jq -e '.resource_group_id.value | length > 0' \
            "$RUNNER_TEMP/level1-management-platform.json" >/dev/null
          jq -e '.log_analytics_workspace_id.value | length > 0' \
            "$RUNNER_TEMP/level1-management-platform.json" >/dev/null
          jq -e '.monitoring_identity_id.value | length > 0' \
            "$RUNNER_TEMP/level1-management-platform.json" >/dev/null

          echo "[PASS] Level 1 Management platform outputs are present."
'''


def desired_files(
    *,
    project_dir: Path,
    foundation: dict[str, Any],
    customer: dict[str, Any],
    platform: dict[str, Any],
    bootstrap: dict[str, Any],
    level1: dict[str, Any],
) -> dict[Path, str]:
    root = project_dir / "levels/level1/management-platform"
    foundation_ref = str(foundation["foundation"]["version"])

    return {
        root / "versions.tf": render_versions(),
        root / "providers.tf": render_provider(),
        root / "variables.tf": render_variables(),
        root / "main.tf": render_main(foundation_ref),
        root / "outputs.tf": render_outputs(),
        root / "backend.tf": render_backend_tf(),
        root / "backend.hcl": render_backend_hcl(
            customer=customer,
            bootstrap=bootstrap,
        ),
        root / "generated.auto.tfvars.json": render_tfvars(
            customer=customer,
            platform=platform,
        ),
        project_dir / MANAGEMENT_SNAPSHOT: render_snapshot(
            customer=customer,
            platform=platform,
            level1=level1,
        ),
        project_dir
        / ".github/workflows/"
        "terraform-level1-management-platform-plan.yml": render_plan_workflow(),
        project_dir
        / ".github/workflows/"
        "terraform-level1-management-platform-apply.yml": render_apply_workflow(),
    }


def changed_files(files: dict[Path, str]) -> list[Path]:
    changed = []
    for path, content in files.items():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current != content:
            changed.append(path)
    return changed


def write_files(files: dict[Path, str]) -> None:
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.resolve()

    print("Azure Platform Foundation Level 1 Management platform")
    print("-----------------------------------------------------")
    print(f"Project: {project_dir}")
    print(f"Mode:    {'apply' if args.apply else 'dry-run'}")
    print()

    try:
        (
            foundation,
            customer,
            platform,
            bootstrap,
            level1,
        ) = require_project(project_dir)

        validate_inputs(
            foundation=foundation,
            customer=customer,
            platform=platform,
            bootstrap=bootstrap,
            level1=level1,
        )

        files = desired_files(
            project_dir=project_dir,
            foundation=foundation,
            customer=customer,
            platform=platform,
            bootstrap=bootstrap,
            level1=level1,
        )

        changes = changed_files(files)
        if not changes:
            print(
                "[PASS] Level 1 Management platform is already generated."
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
        print("[PASS] Level 1 Management platform generated.")
        print("[PASS] No Azure resources were changed.")
        return 0

    except (ConfigureError, OSError, KeyError, TypeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
