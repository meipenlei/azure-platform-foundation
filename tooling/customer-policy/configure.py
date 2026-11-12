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
    / "audit-first-wave1.json"
)

PAC_SELECTOR = "apf-governance"
LEVEL1_SNAPSHOT = ".foundation/level1-management-groups.yaml"
APPLY_GUARD_SOURCE = Path(__file__).with_name("verify_apply_plan.py")
MANAGEMENT_GROUP_SCOPE_PREFIX = (
    "/providers/Microsoft.Management/managementGroups/"
)
POLICY_ASSIGNMENT_NAME_MAX_LENGTH = 24

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
            "Generate the APF EPAC desired state and protected apply workflow in an existing "
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


def management_group_ids(level1: dict[str, Any]) -> dict[str, str]:
    try:
        raw = level1["management_groups"]["management_group_ids"]
    except (KeyError, TypeError) as exc:
        raise ConfigureError(
            f"{LEVEL1_SNAPSHOT} does not contain management_group_ids."
        ) from exc

    if not isinstance(raw, dict):
        raise ConfigureError(
            f"{LEVEL1_SNAPSHOT} management_group_ids must be an object."
        )

    result: dict[str, str] = {}

    for key, value in raw.items():
        scope = str(value)
        if not scope.startswith(MANAGEMENT_GROUP_SCOPE_PREFIX):
            raise ConfigureError(
                f"Management-group scope '{key}' is invalid: {scope}"
            )
        result[str(key)] = scope

    return result


def deployment_root_scope(level1: dict[str, Any]) -> str:
    try:
        scope = str(
            level1["management_groups"]["policy_deployment_root_scope"]
        )
    except (KeyError, TypeError) as exc:
        raise ConfigureError(
            f"{LEVEL1_SNAPSHOT} does not contain "
            "policy_deployment_root_scope."
        ) from exc

    groups = management_group_ids(level1)
    root_scope = groups.get("root")

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


def assignment_scope(
    level1: dict[str, Any],
    assignment: dict[str, Any],
) -> str:
    scope_key = str(assignment.get("scope_key", ""))
    groups = management_group_ids(level1)

    if not scope_key:
        raise ConfigureError("Policy assignment scope_key is required.")

    if scope_key not in groups:
        raise ConfigureError(
            f"Policy assignment references unknown Level 1 scope_key "
            f"'{scope_key}'."
        )

    return groups[scope_key]


def validate_profile(
    profile: dict[str, Any],
    level1: dict[str, Any],
) -> None:
    assignments = profile.get("assignments")

    if not isinstance(assignments, list) or len(assignments) < 2:
        raise ConfigureError(
            "Scope-aware Wave 1 must contain multiple assignments."
        )

    seen_keys: set[str] = set()
    seen_files: set[str] = set()
    seen_names: set[str] = set()

    for assignment in assignments:
        if not isinstance(assignment, dict):
            raise ConfigureError(
                "Every profile assignment must be an object."
            )

        key = str(assignment.get("key", ""))
        file_name = str(assignment.get("file_name", ""))
        assignment_name = str(
            (assignment.get("assignment") or {}).get("name", "")
        )

        if not key or key in seen_keys:
            raise ConfigureError(
                f"Policy assignment key must be unique: {key!r}"
            )
        if (
            not file_name
            or not file_name.endswith(".assignment.jsonc")
            or file_name in seen_files
        ):
            raise ConfigureError(
                f"Policy assignment file_name is invalid or duplicate: "
                f"{file_name!r}"
            )
        if not assignment_name or assignment_name in seen_names:
            raise ConfigureError(
                f"Azure policy assignment name is invalid or duplicate: "
                f"{assignment_name!r}"
            )
        if len(assignment_name) > POLICY_ASSIGNMENT_NAME_MAX_LENGTH:
            raise ConfigureError(
                f"Azure policy assignment name {assignment_name!r} is "
                f"{len(assignment_name)} characters long; management-group "
                f"assignments are limited to "
                f"{POLICY_ASSIGNMENT_NAME_MAX_LENGTH} characters."
            )

        assignment_scope(level1, assignment)

        enforcement = assignment.get("enforcement_mode")
        if enforcement not in ("Default", "DoNotEnforce"):
            raise ConfigureError(
                f"Unsupported enforcement_mode for {key}: {enforcement!r}"
            )

        definition = assignment.get("definition") or {}
        if not definition.get("id"):
            raise ConfigureError(
                f"Policy definition ID is required for {key}."
            )
        if not definition.get("definition_version"):
            raise ConfigureError(
                f"Policy definition version is required for {key}."
            )

        seen_keys.add(key)
        seen_files.add(file_name)
        seen_names.add(assignment_name)


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
                "Scope-aware Wave 1 must use "
                "desiredState.strategy=ownedOnly."
            )

        if profile["stage"] != "scope_aware_wave1":
            raise ConfigureError(
                "Active policy profile must use scope_aware_wave1."
            )

        if profile.get("scope_source") != LEVEL1_SNAPSHOT:
            raise ConfigureError(
                "Scope-aware Wave 1 must derive scopes from "
                "the Level 1 snapshot."
            )

        validate_profile(profile, level1)

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
                "deploymentRootScope": deployment_root_scope(level1),
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
    assignment: dict[str, Any],
) -> str:
    definition = assignment["definition"]
    assignment_meta = assignment["assignment"]

    document = {
        "$schema": (
            "https://raw.githubusercontent.com/"
            "Azure/enterprise-azure-policy-as-code/main/"
            "Schemas/policy-assignment-schema.json"
        ),
        "nodeName": (
            f"/APF/Enterprise/AuditFirst/Wave1/"
            f"{assignment['key']}/"
        ),
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
            "apfScopeKey": assignment["scope_key"],
            "apfUpstreamAssignment": assignment["upstream_assignment"],
            "apfUpstreamAlzTag": profile["upstream"]["alz_tag"],
            "apfLegacyAssignment": assignment["legacy_assignment"],
            "apfLegacyArchetype": assignment["legacy_archetype"],
        },
        "enforcementMode": assignment["enforcement_mode"],
        "parameters": assignment.get("parameters", {}),
        "scope": {
            PAC_SELECTOR: [
                assignment_scope(level1, assignment)
            ]
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
    scopes = {
        assignment["key"]: {
            "scope_key": assignment["scope_key"],
            "scope": assignment_scope(level1, assignment),
        }
        for assignment in profile["assignments"]
    }

    data = {
        "schema_version": "0.1",
        "generator": "apf-customer-policy",
        "mode": "protected_apply",
        "pac_owner_id": owner_id,
        "pac_selector": PAC_SELECTOR,
        "deployment_root_scope": deployment_root_scope(level1),
        "deployment_root_source": LEVEL1_SNAPSHOT,
        "desired_state_strategy": profile["desired_state_strategy"],
        "profile": {
            "name": profile["name"],
            "adoption_mode": profile["adoption_mode"],
            "stage": profile["stage"],
            "assignment_count": len(profile["assignments"]),
        },
        "assignment_scopes": scopes,
        "ci_cd": {
            "plan_workflow": ".github/workflows/policy-plan.yml",
            "apply_workflow": ".github/workflows/policy-apply.yml",
            "apply_environment": "apf-governance",
            "apply_guard": "additive_assignments_only",
        },
        "toolchain": {
            "epac": versions["epac"]["version"],
            "alz": versions["azure_landing_zones_library"]["alz_tag"],
            "slz": versions["azure_landing_zones_library"]["slz_tag"],
        },
    }

    return yaml.safe_dump(data, sort_keys=False)


def render_plan_workflow(
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
      - ".github/workflows/policy-apply.yml"

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

      - name: Detect EPAC plan output
        id: plan-output
        shell: bash
        run: |
          if find governance/policy/Output -type f -print -quit 2>/dev/null | grep -q .; then
            echo "has_plan=true" >> "$GITHUB_OUTPUT"
            echo "[PASS] EPAC deployment plan artifact detected."
          else
            echo "has_plan=false" >> "$GITHUB_OUTPUT"
            echo "[PASS] EPAC desired state is converged; no deployment plan artifact was produced."
          fi

      - name: Upload EPAC plan
        if: steps.plan-output.outputs.has_plan == 'true'
        uses: actions/upload-artifact@v7
        with:
          name: epac-policy-plan-${{{{ github.event.pull_request.number }}}}
          path: governance/policy/Output/
          if-no-files-found: error
'''


def render_apply_workflow(
    *,
    customer: dict[str, Any],
    versions: dict[str, Any],
) -> str:
    epac_version = versions["epac"]["version"]
    azure_environment = CLOUD_MAP[customer["azure"]["cloud"]]

    return f'''name: Policy Desired State Apply

on:
  workflow_dispatch:
    inputs:
      confirm_apply:
        description: "Confirm deployment of the current main-branch policy desired state"
        required: true
        default: false
        type: boolean

permissions:
  contents: read
  id-token: write

env:
  AZURE_CORE_OUTPUT: "none"
  EPAC_VERSION: "{epac_version}"
  PAC_SELECTOR: "{PAC_SELECTOR}"
  POLICY_DEFINITIONS_ROOT: "${{{{ github.workspace }}}}/governance/policy/Definitions"
  POLICY_OUTPUT: "${{{{ github.workspace }}}}/governance/policy/Output"
  POLICY_POST_APPLY_OUTPUT: "${{{{ github.workspace }}}}/governance/policy/PostApplyOutput"
  POST_APPLY_MAX_ATTEMPTS: "5"
  POST_APPLY_RETRY_SECONDS: "30"

jobs:
  policy-apply:
    name: EPAC Policy Apply
    if: ${{{{ github.ref == 'refs/heads/main' && inputs.confirm_apply == true }}}}
    runs-on: ubuntu-24.04

    environment:
      name: apf-governance

    steps:
      - name: Checkout repository
        uses: actions/checkout@v7

      - name: Setup Python
        uses: actions/setup-python@v7
        with:
          python-version: "3.12"

      - name: Azure login with Governance identity
        uses: azure/login@v3
        with:
          client-id: ${{{{ vars.AZURE_GOVERNANCE_CLIENT_ID }}}}
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

          foreach ($command in @(
            "Build-DeploymentPlans",
            "Deploy-PolicyPlan",
            "Deploy-RolesPlan"
          )) {{
            if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {{
              throw "$command is not available."
            }}
          }}

      - name: Build protected apply plan
        shell: pwsh
        run: |
          $ErrorActionPreference = "Stop"

          Build-DeploymentPlans `
            -DefinitionsRootFolder $env:POLICY_DEFINITIONS_ROOT `
            -PacEnvironmentSelector $env:PAC_SELECTOR `
            -OutputFolder $env:POLICY_OUTPUT

      - name: Verify additive-only apply boundary
        shell: bash
        run: |
          python governance/policy/tooling/verify_apply_plan.py \\
            --mode pre-apply \\
            --definitions-root "$POLICY_DEFINITIONS_ROOT" \\
            --pac-selector "$PAC_SELECTOR" \\
            --policy-plan "$POLICY_OUTPUT/plans-$PAC_SELECTOR/policy-plan.json" \\
            --roles-plan "$POLICY_OUTPUT/plans-$PAC_SELECTOR/roles-plan.json"

      - name: Upload protected apply plan
        uses: actions/upload-artifact@v7
        with:
          name: epac-policy-apply-plan-${{{{ github.run_id }}}}
          path: governance/policy/Output/
          if-no-files-found: warn

      - name: Deploy EPAC policy plan
        shell: pwsh
        run: |
          $ErrorActionPreference = "Stop"

          Deploy-PolicyPlan `
            -DefinitionsRootFolder $env:POLICY_DEFINITIONS_ROOT `
            -PacEnvironmentSelector $env:PAC_SELECTOR `
            -InputFolder $env:POLICY_OUTPUT

      - name: Deploy EPAC roles plan
        shell: pwsh
        run: |
          $ErrorActionPreference = "Stop"

          Deploy-RolesPlan `
            -DefinitionsRootFolder $env:POLICY_DEFINITIONS_ROOT `
            -PacEnvironmentSelector $env:PAC_SELECTOR `
            -InputFolder $env:POLICY_OUTPUT

      - name: Verify post-apply convergence with bounded retry
        shell: pwsh
        run: |
          $ErrorActionPreference = "Stop"

          $maxAttempts = [int]$env:POST_APPLY_MAX_ATTEMPTS
          $retrySeconds = [int]$env:POST_APPLY_RETRY_SECONDS

          for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {{
            Write-Host "Post-apply convergence attempt $attempt of $maxAttempts."

            if (Test-Path $env:POLICY_POST_APPLY_OUTPUT) {{
              Remove-Item `
                -Path $env:POLICY_POST_APPLY_OUTPUT `
                -Recurse `
                -Force
            }}

            Build-DeploymentPlans `
              -DefinitionsRootFolder $env:POLICY_DEFINITIONS_ROOT `
              -PacEnvironmentSelector $env:PAC_SELECTOR `
              -OutputFolder $env:POLICY_POST_APPLY_OUTPUT

            & python governance/policy/tooling/verify_apply_plan.py `
              --mode post-apply `
              --definitions-root $env:POLICY_DEFINITIONS_ROOT `
              --pac-selector $env:PAC_SELECTOR `
              --policy-plan "$env:POLICY_POST_APPLY_OUTPUT/plans-$env:PAC_SELECTOR/policy-plan.json" `
              --roles-plan "$env:POLICY_POST_APPLY_OUTPUT/plans-$env:PAC_SELECTOR/roles-plan.json"

            $verifyExit = $LASTEXITCODE

            if ($verifyExit -eq 0) {{
              exit 0
            }}

            if ($verifyExit -ne 3) {{
              throw "Post-apply verification failed with non-retryable exit code $verifyExit."
            }}

            if ($attempt -eq $maxAttempts) {{
              throw "Post-apply convergence did not complete after $maxAttempts attempts."
            }}

            Write-Warning (
              "Azure policy state has not converged yet. " +
              "Retrying in $retrySeconds seconds."
            )
            Start-Sleep -Seconds $retrySeconds
          }}
'''

def render_policy_readme(
    *,
    profile: dict[str, Any],
    level1: dict[str, Any],
) -> str:
    lines = [
        "# APF Policy Desired State",
        "",
        "This directory is generated by Azure Platform Foundation.",
        "",
        "## Current stage",
        "",
        f"Profile: `{profile['name']}`  ",
        f"Adoption mode: `{profile['adoption_mode']}`  ",
        f"Stage: `{profile['stage']}`  ",
        f"Desired-state strategy: `{profile['desired_state_strategy']}`  ",
        f"Deployment root: `{deployment_root_scope(level1)}`",
        "",
        "## Scope-aware Wave 1",
        "",
        "| Assignment | Legacy archetype | APF scope | Behavior |",
        "| --- | --- | --- | --- |",
    ]

    for assignment in profile["assignments"]:
        behavior = (
            f"{assignment['enforcement_mode']}; "
            f"effect={assignment.get('parameters', {}).get('effect', 'n/a')}"
        )
        lines.append(
            f"| `{assignment['upstream_assignment']}` "
            f"| `{assignment['legacy_archetype']}` "
            f"| `{assignment['scope_key']}` "
            f"| `{behavior}` |"
        )

    lines.extend(
        [
            "",
            "Scopes are resolved from:",
            "",
            f"    {LEVEL1_SNAPSHOT}",
            "",
            "The generator does not infer missing archetype mappings.",
            "",
            "## Ownership",
            "",
            "The EPAC environment continues to use:",
            "",
            "    desiredState.strategy = ownedOnly",
            "",
            "Existing policies not owned by this EPAC instance are not deletion candidates.",
            "",
            "## CI/CD",
            "",
            "`policy-plan.yml` remains pull-request-only and uses the APF Plan identity.",
            "",
            "`policy-apply.yml` is manual-only, runs from `main`, uses the protected",
            "`apf-governance` environment and authenticates with the Governance identity.",
            "",
            "Before any Azure mutation, the apply workflow rebuilds the EPAC plan and",
            "runs an APF guard that allows only additive policy assignments already",
            "present in the generated Definitions tree. Deletes, replaces, updates,",
            "policy definitions, policy sets, exemptions and role changes are blocked.",
            "",
            "After deployment, the workflow rebuilds the plan and requires convergence",
            "to zero remaining policy or role changes.",
            "",
        ]
    )

    return "\n".join(lines)

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

    files = {
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
            / "governance/policy/README.md"
        ): render_policy_readme(
            profile=profile,
            level1=level1,
        ),
        (
            project_dir
            / "governance/policy/tooling/verify_apply_plan.py"
        ): APPLY_GUARD_SOURCE.read_text(encoding="utf-8"),
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
        ): render_plan_workflow(
            customer=customer,
            versions=versions,
        ),
        (
            project_dir
            / ".github/workflows/policy-apply.yml"
        ): render_apply_workflow(
            customer=customer,
            versions=versions,
        ),
    }

    assignment_dir = (
        project_dir
        / "governance/policy/Definitions/policyAssignments"
    )

    for assignment in profile["assignments"]:
        files[
            assignment_dir / assignment["file_name"]
        ] = render_assignment(
            level1=level1,
            profile=profile,
            assignment=assignment,
        )

    return files


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
        existing + suffix + marker + "\n" + entry + "\n",
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
        customer, platform, discovery, level1 = verify_project(project_dir)
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
        print("[PASS] APF scope-aware Wave 1 desired state and protected apply workflow generated.")
        print(
            "[PASS] No Azure Policy resources were changed by the generator; "
            "Azure mutation remains isolated to the protected manual apply workflow."
        )
        return 0

    except (ConfigureError, OSError, KeyError, TypeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
