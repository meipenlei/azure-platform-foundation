#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_PATH = REPO_ROOT / "foundation" / "policy" / "versions.json"
PROFILE_PATH = (
    REPO_ROOT
    / "foundation"
    / "policy"
    / "profiles"
    / "enterprise"
    / "audit-first-management-group-pilot.json"
)

PAC_SELECTOR = "apf-governance"
LEVEL1_SNAPSHOT = ".foundation/level1-management-groups.yaml"
MANAGEMENT_GROUP_SCOPE_PREFIX = "/providers/Microsoft.Management/managementGroups/"

CLOUD_MAP = {
    "public": "AzureCloud",
    "usgovernment": "AzureUSGovernment",
    "china": "AzureChinaCloud",
}


class ConfigureError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the APF EPAC plan-only desired state in an existing "
            "customer repository."
        )
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Existing APF customer repository.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write generated files. Without this flag the command is dry-run only.",
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


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigureError(f"Unable to read JSON '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigureError(f"JSON '{path}' must contain an object.")

    return data


def verify_project(
    project_dir: Path,
) -> tuple[dict, dict, dict, dict]:
    required = {
        "customer": project_dir / "config" / "customer.yaml",
        "platform": project_dir / "config" / "platform.yaml",
        "discovery": project_dir / ".foundation" / "discovery.yaml",
        "level1": project_dir / LEVEL1_SNAPSHOT,
    }

    missing = [
        str(path)
        for path in required.values()
        if not path.is_file()
    ]
    if missing:
        raise ConfigureError(
            "The project is missing required APF files:\n  - "
            + "\n  - ".join(missing)
        )

    return (
        load_yaml(required["customer"]),
        load_yaml(required["platform"]),
        load_yaml(required["discovery"]),
        load_yaml(required["level1"]),
    )


def deployment_root_scope(level1: dict[str, Any]) -> str:
    try:
        management_groups = level1["management_groups"]
        scope = str(management_groups["policy_deployment_root_scope"])
        root_scope = str(management_groups["management_group_ids"]["root"])
    except (KeyError, TypeError) as exc:
        raise ConfigureError(
            f"{LEVEL1_SNAPSHOT} does not contain the required "
            "Level 1 management-group outputs."
        ) from exc

    if not scope.startswith(MANAGEMENT_GROUP_SCOPE_PREFIX):
        raise ConfigureError(
            "Level 1 policy_deployment_root_scope must be a "
            f"management-group scope, got: {scope}"
        )

    if scope != root_scope:
        raise ConfigureError(
            "Level 1 policy_deployment_root_scope does not match "
            "management_group_ids.root."
        )

    return scope


def validate_inputs(
    customer: dict[str, Any],
    platform: dict[str, Any],
    discovery: dict[str, Any],
    level1: dict[str, Any],
    versions: dict[str, Any],
    profile: dict[str, Any],
) -> None:
    try:
        if platform["execution"]["provider"] != "github":
            raise ConfigureError(
                "Policy-plan generation supports GitHub execution only."
            )

        azure_cloud = customer["azure"]["cloud"]
        if azure_cloud not in CLOUD_MAP:
            raise ConfigureError(
                f"Unsupported Azure cloud for policy planning: {azure_cloud}"
            )

        github = discovery["github"]
        if not github.get("owner_id") or not github.get("repository_id"):
            raise ConfigureError(
                "Immutable GitHub owner/repository IDs are required."
            )

        if level1.get("source") != "terraform-level1-management-groups":
            raise ConfigureError(
                f"{LEVEL1_SNAPSHOT} is not an APF Level 1 Terraform snapshot."
            )

        deployment_root_scope(level1)

        library = versions["azure_landing_zones_library"]
        if profile["upstream"]["alz_tag"] != library["alz_tag"]:
            raise ConfigureError(
                "Policy profile ALZ tag does not match "
                "foundation/policy/versions.json."
            )

        if profile["desired_state_strategy"] != "ownedOnly":
            raise ConfigureError(
                "Management-group pilot must use "
                "desiredState.strategy=ownedOnly."
            )

        if profile["stage"] != "management_group_pilot":
            raise ConfigureError(
                "Active policy profile must use management_group_pilot."
            )

        if profile.get("scope_source") != LEVEL1_SNAPSHOT:
            raise ConfigureError(
                "Management-group pilot must derive its scope from "
                "the Level 1 snapshot."
            )
    except KeyError as exc:
        raise ConfigureError(
            f"Required APF configuration field is missing: {exc}"
        ) from exc


def pac_owner_id(discovery: dict[str, Any]) -> str:
    github = discovery["github"]
    seed = (
        "apf-policy://github/"
        f"{github['owner_id']}/"
        f"{github['repository_id']}"
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def render_global_settings(
    *,
    customer: dict[str, Any],
    level1: dict[str, Any],
    owner_id: str,
    strategy: str,
) -> str:
    scope = deployment_root_scope(level1)

    document = {
        "$schema": (
            "https://raw.githubusercontent.com/"
            "Azure/enterprise-azure-policy-as-code/main/"
            "Schemas/global-settings-schema.json"
        ),
        "telemetryOptOut": True,
        "pacOwnerId": owner_id,
        "pacEnvironments": [
            {
                "pacSelector": PAC_SELECTOR,
                "cloud": CLOUD_MAP[customer["azure"]["cloud"]],
                "tenantId": customer["azure"]["tenant_id"],
                "deploymentRootScope": scope,
                "managedIdentityLocation": customer["azure"]["primary_region"],
                "skipResourceValidationForExemptions": False,
                "desiredState": {
                    "strategy": strategy,
                    "keepDfcSecurityAssignments": False,
                    "doNotDisableDeprecatedPolicies": False,
                    "manageChildScopeDefinitions": False,
                },
            }
        ],
    }

    return json.dumps(document, indent=2) + "\n"


def render_assignment(
    *,
    level1: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    assignment = profile["assignments"][0]
    definition = assignment["definition"]
    assignment_meta = assignment["assignment"]
    scope = deployment_root_scope(level1)

    document = {
        "$schema": (
            "https://raw.githubusercontent.com/"
            "Azure/enterprise-azure-policy-as-code/main/"
            "Schemas/policy-assignment-schema.json"
        ),
        "nodeName": "/APF/Enterprise/AuditFirst/PublicIP/",
        "definitionEntry": {
            "policyId": definition["id"],
            "definitionVersion": definition["definition_version"],
            "displayName": definition["display_name"],
        },
        "assignment": {
            "name": assignment_meta["name"],
            "displayName": assignment_meta["display_name"],
            "description": assignment_meta["description"],
        },
        "metadata": {
            "apfProfile": profile["name"],
            "apfAdoptionMode": profile["adoption_mode"],
            "apfStage": profile["stage"],
            "apfScopeSource": profile["scope_source"],
            "apfUpstreamAssignment": profile["upstream"]["assignment"],
            "apfUpstreamAlzTag": profile["upstream"]["alz_tag"],
            "apfLegacyAssignment": (
                profile["migration_provenance"]["legacy_assignment"]
            ),
        },
        "enforcementMode": assignment["enforcement_mode"],
        "parameters": assignment["parameters"],
        "scope": {
            PAC_SELECTOR: [scope]
        },
    }

    return json.dumps(document, indent=2) + "\n"


def render_policy_metadata(
    *,
    versions: dict[str, Any],
    profile: dict[str, Any],
    owner_id: str,
    level1: dict[str, Any],
) -> str:
    data = {
        "schema_version": "0.1",
        "generator": "apf-customer-policy",
        "mode": "plan_only",
        "pac_owner_id": owner_id,
        "pac_selector": PAC_SELECTOR,
        "deployment_root_scope": deployment_root_scope(level1),
        "deployment_root_source": LEVEL1_SNAPSHOT,
        "desired_state_strategy": profile["desired_state_strategy"],
        "profile": {
            "name": profile["name"],
            "adoption_mode": profile["adoption_mode"],
            "stage": profile["stage"],
        },
        "toolchain": {
            "epac": versions["epac"]["version"],
            "alz": versions["azure_landing_zones_library"]["alz_tag"],
            "slz": versions["azure_landing_zones_library"]["slz_tag"],
        },
    }

    return yaml.safe_dump(data, sort_keys=False)


def render_workflow(
    *,
    customer: dict[str, Any],
    versions: dict[str, Any],
) -> str:
    epac_version = versions["epac"]["version"]
    azure_environment = CLOUD_MAP[customer["azure"]["cloud"]]

    return f'''name: Policy Desired State Plan

on:
  pull_request:
    paths:
      - "governance/policy/**"
      - ".foundation/policy.yaml"
      - ".foundation/level1-management-groups.yaml"
      - ".github/workflows/policy-plan.yml"

permissions:
  contents: read
  id-token: write

env:
  AZURE_CORE_OUTPUT: "none"
  EPAC_VERSION: "{epac_version}"
  PAC_SELECTOR: "{PAC_SELECTOR}"

jobs:
  policy-plan:
    name: EPAC Policy Plan
    runs-on: ubuntu-24.04

    steps:
      - name: Checkout repository
        uses: actions/checkout@v7

      - name: Azure login with Plan identity
        uses: azure/login@v3
        with:
          client-id: ${{{{ vars.AZURE_PLAN_CLIENT_ID }}}}
          tenant-id: ${{{{ vars.AZURE_TENANT_ID }}}}
          subscription-id: ${{{{ vars.AZURE_SUBSCRIPTION_ID }}}}
          environment: "{azure_environment}"
          enable-AzPSSession: true

      - name: Install pinned EPAC module
        shell: pwsh
        run: |
          $ErrorActionPreference = "Stop"

          Install-Module `
            -Name EnterprisePolicyAsCode `
            -RequiredVersion $env:EPAC_VERSION `
            -Repository PSGallery `
            -Scope CurrentUser `
            -Force `
            -AllowClobber

          Import-Module `
            -Name EnterprisePolicyAsCode `
            -RequiredVersion $env:EPAC_VERSION `
            -Force

          if (-not (Get-Command Build-DeploymentPlans -ErrorAction SilentlyContinue)) {{
            throw "Build-DeploymentPlans is not available."
          }}

      - name: Build EPAC deployment plan
        shell: pwsh
        run: |
          $ErrorActionPreference = "Stop"

          Build-DeploymentPlans `
            -DefinitionsRootFolder "${{{{ github.workspace }}}}/governance/policy/Definitions" `
            -PacEnvironmentSelector $env:PAC_SELECTOR `
            -OutputFolder "${{{{ github.workspace }}}}/governance/policy/Output"

      - name: Upload EPAC plan
        uses: actions/upload-artifact@v7
        with:
          name: epac-policy-plan-${{{{ github.event.pull_request.number }}}}
          path: governance/policy/Output/
          if-no-files-found: error
'''


def render_policy_readme(
    *,
    profile: dict[str, Any],
    level1: dict[str, Any],
) -> str:
    scope = deployment_root_scope(level1)

    return f'''# APF Policy Desired State

This directory is generated by Azure Platform Foundation.

## Current stage

Profile: `{profile["name"]}`  
Adoption mode: `{profile["adoption_mode"]}`  
Stage: `{profile["stage"]}`  
Desired-state strategy: `{profile["desired_state_strategy"]}`  
Deployment root: `{scope}`

The deployment root is derived from:

    {LEVEL1_SNAPSHOT}

## Pilot assignment

The desired-state slice still contains one audit-only policy assignment:

    APF - Audit public IP creation

It preserves the legacy `CAF-Deny-Public-IP` behavior:

    effect = Audit
    enforcementMode = Default
    definitionVersion = 2.*.*

The assignment is now scoped to the APF root management group and therefore
covers its child management groups and subscriptions.

## Ownership

The EPAC environment continues to use:

    desiredState.strategy = ownedOnly

Existing policies not owned by this EPAC instance are not deletion candidates.

## CI/CD

`.github/workflows/policy-plan.yml` remains PR-only and uses the APF Plan
identity.

There is still no Policy Apply workflow.
'''


def desired_files(
    *,
    project_dir: Path,
    customer: dict[str, Any],
    versions: dict[str, Any],
    profile: dict[str, Any],
    discovery: dict[str, Any],
    level1: dict[str, Any],
) -> dict[Path, str]:
    owner_id = pac_owner_id(discovery)

    return {
        (
            project_dir
            / "governance/policy/Definitions/global-settings.jsonc"
        ): render_global_settings(
            customer=customer,
            level1=level1,
            owner_id=owner_id,
            strategy=profile["desired_state_strategy"],
        ),
        (
            project_dir
            / "governance/policy/Definitions/policyAssignments/"
            "apf-audit-public-ip.assignment.jsonc"
        ): render_assignment(
            level1=level1,
            profile=profile,
        ),
        (
            project_dir
            / "governance/policy/README.md"
        ): render_policy_readme(
            profile=profile,
            level1=level1,
        ),
        (
            project_dir
            / ".foundation/policy.yaml"
        ): render_policy_metadata(
            versions=versions,
            profile=profile,
            owner_id=owner_id,
            level1=level1,
        ),
        (
            project_dir
            / ".github/workflows/policy-plan.yml"
        ): render_workflow(
            customer=customer,
            versions=versions,
        ),
    }


def ensure_gitignore(project_dir: Path) -> tuple[Path, str]:
    path = project_dir / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""

    marker = "# APF EPAC generated plans"
    entry = "governance/policy/Output/"

    if marker in existing or entry in existing.splitlines():
        return path, existing

    suffix = (
        ""
        if not existing or existing.endswith("\n\n")
        else ("\n" if existing.endswith("\n") else "\n\n")
    )

    return (
        path,
        existing
        + suffix
        + marker
        + "\n"
        + entry
        + "\n",
    )


def changed_files(files: dict[Path, str]) -> list[Path]:
    changed = []

    for path, content in files.items():
        current = (
            path.read_text(encoding="utf-8")
            if path.is_file()
            else None
        )
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

    print("Azure Platform Foundation customer policy configuration")
    print("------------------------------------------------------")
    print(f"Project: {project_dir}")
    print(f"Mode:    {'apply' if args.apply else 'dry-run'}")
    print()

    try:
        (
            customer,
            platform,
            discovery,
            level1,
        ) = verify_project(project_dir)

        versions = load_json(VERSIONS_PATH)
        profile = load_json(PROFILE_PATH)

        validate_inputs(
            customer=customer,
            platform=platform,
            discovery=discovery,
            level1=level1,
            versions=versions,
            profile=profile,
        )

        files = desired_files(
            project_dir=project_dir,
            customer=customer,
            versions=versions,
            profile=profile,
            discovery=discovery,
            level1=level1,
        )

        gitignore_path, gitignore_content = ensure_gitignore(project_dir)
        files[gitignore_path] = gitignore_content

        changes = changed_files(files)

        if not changes:
            print("[PASS] Customer policy desired state is already generated.")
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
        print("[PASS] APF management-group policy desired state generated.")
        print(
            "[PASS] No Azure Policy resources were changed; "
            "the generated workflow runs Build-DeploymentPlans only."
        )
        return 0

    except (ConfigureError, OSError, KeyError, TypeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
