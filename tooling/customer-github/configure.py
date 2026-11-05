#!/usr/bin/env python3

"""
Azure Platform Foundation GitHub configuration lifecycle.

Commit 6 scope:
- validates a customer repository and GitHub CLI authentication
- initializes the existing Level 0 bootstrap backend read-only
- reads bootstrap outputs
- discovers immutable GitHub owner/repository IDs
- validates the three APF GitHub OIDC subjects
- checks the expected GitHub environments
- checks repository/environment Actions variables
- applies GitHub configuration only when --apply is supplied
- verifies the resulting GitHub configuration

This tool does not create Azure resources and does not use long-lived
Azure client secrets.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml


TERRAFORM_REQUIRED_VERSION_PREFIX = "Terraform v1.17."

LEVEL0_ENVIRONMENT = "apf-level0"
GOVERNANCE_ENVIRONMENT = "apf-governance"

WORKFLOW_FILES = (
    "terraform-plan.yml",
    "terraform-apply.yml",
    "terraform-governance-plan.yml",
    "terraform-governance-apply.yml",
)


class GitHubConfigurationError(RuntimeError):
    """Raised when APF GitHub configuration cannot be completed."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Configure GitHub for an Azure Platform Foundation "
            "customer repository."
        )
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path("."),
        help=(
            "APF customer repository. Defaults to the current directory."
        ),
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Create/update GitHub environments and Actions variables. "
            "Without this flag the tool performs a read-only plan."
        ),
    )

    return parser.parse_args()


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(command)
    print(f"+ {printable}")

    result = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=capture_output,
        text=True,
        input=input_text,
    )

    if check and result.returncode != 0:
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""

        details = "\n".join(
            part for part in (stdout, stderr) if part
        )

        if details:
            raise GitHubConfigurationError(
                f"Command failed ({result.returncode}): "
                f"{printable}\n{details}"
            )

        raise GitHubConfigurationError(
            f"Command failed ({result.returncode}): {printable}"
        )

    return result


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise GitHubConfigurationError(
            f"Required command '{name}' was not found in PATH."
        )


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = yaml.safe_load(handle)
    except OSError as exc:
        raise GitHubConfigurationError(
            f"Unable to read YAML file '{path}': {exc}"
        ) from exc
    except yaml.YAMLError as exc:
        raise GitHubConfigurationError(
            f"Invalid YAML file '{path}': {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise GitHubConfigurationError(
            f"YAML file '{path}' must contain an object."
        )

    return data


def verify_project_structure(
    project_dir: Path,
) -> Path:
    bootstrap_dir = (
        project_dir
        / "levels"
        / "level0"
        / "bootstrap"
    )

    required_paths = (
        project_dir / "config" / "customer.yaml",
        project_dir / "config" / "platform.yaml",
        bootstrap_dir / "backend.tf",
        bootstrap_dir / "backend.hcl",
        bootstrap_dir / "main.tf",
        bootstrap_dir / "outputs.tf",
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

        raise GitHubConfigurationError(
            "The project is not ready for GitHub configuration. "
            f"Missing files:\n{formatted}\n"
            "Run customer-bootstrap --apply first."
        )

    return bootstrap_dir


def verify_workflow_contract(
    project_dir: Path,
) -> None:
    workflow_dir = (
        project_dir
        / ".github"
        / "workflows"
    )

    missing = [
        name
        for name in WORKFLOW_FILES
        if not (workflow_dir / name).is_file()
    ]

    if missing:
        formatted = "\n".join(
            f"  - .github/workflows/{name}"
            for name in missing
        )

        raise GitHubConfigurationError(
            "Generated APF GitHub workflows are missing:\n"
            f"{formatted}"
        )

    required_tokens = {
        "terraform-plan.yml": (
            "vars.AZURE_PLAN_CLIENT_ID",
            "vars.AZURE_TENANT_ID",
            "vars.AZURE_SUBSCRIPTION_ID",
        ),
        "terraform-apply.yml": (
            "vars.AZURE_APPLY_CLIENT_ID",
            "vars.AZURE_TENANT_ID",
            "vars.AZURE_SUBSCRIPTION_ID",
        ),
        "terraform-governance-plan.yml": (
            "vars.AZURE_GOVERNANCE_CLIENT_ID",
            "vars.AZURE_TENANT_ID",
            "vars.AZURE_SUBSCRIPTION_ID",
        ),
        "terraform-governance-apply.yml": (
            "vars.AZURE_GOVERNANCE_CLIENT_ID",
            "vars.AZURE_TENANT_ID",
            "vars.AZURE_SUBSCRIPTION_ID",
        ),
    }

    for filename, tokens in required_tokens.items():
        content = (
            workflow_dir
            / filename
        ).read_text(
            encoding="utf-8"
        )

        if "secrets.AZURE_" in content:
            raise GitHubConfigurationError(
                f"{filename} still uses legacy secrets.AZURE_* "
                "references. Regenerate/copy the current APF workflows "
                "before configuring GitHub variables."
            )

        for token in tokens:
            if token not in content:
                raise GitHubConfigurationError(
                    f"{filename} does not contain expected "
                    f"workflow reference '{token}'."
                )

    print(
        "[PASS] Customer workflows use the APF GitHub Variables contract."
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
        raise GitHubConfigurationError(
            "APF currently requires Terraform 1.17.x. "
            f"Detected: {first_line or 'unknown'}"
        )

    print(f"[PASS] {first_line}")


def verify_github_authentication() -> None:
    result = run_command(
        [
            "gh",
            "api",
            "user",
            "--jq",
            ".login",
        ],
        capture_output=True,
    )

    login = result.stdout.strip()

    if not login:
        raise GitHubConfigurationError(
            "GitHub CLI authentication could not be verified."
        )

    print(
        f"[PASS] GitHub CLI authenticated as {login}."
    )


def load_customer_context(
    project_dir: Path,
) -> tuple[str, str, str, str]:
    customer = load_yaml(
        project_dir
        / "config"
        / "customer.yaml"
    )

    platform = load_yaml(
        project_dir
        / "config"
        / "platform.yaml"
    )

    try:
        tenant_id = str(
            customer["azure"]["tenant_id"]
        )
        subscription_id = str(
            customer["azure"]["bootstrap_subscription_id"]
        )

        if platform["execution"]["provider"] != "github":
            raise GitHubConfigurationError(
                "customer-github currently requires "
                "execution.provider='github'."
            )

        github = platform["execution"]["github"]

        owner = str(
            github["owner"]
        )
        repository = str(
            github["repository"]
        )
    except (KeyError, TypeError) as exc:
        raise GitHubConfigurationError(
            "Customer/platform configuration does not contain the "
            "required Azure and GitHub fields."
        ) from exc

    values = (
        tenant_id,
        subscription_id,
        owner,
        repository,
    )

    if any(not value for value in values):
        raise GitHubConfigurationError(
            "Customer/platform configuration contains empty required fields."
        )

    return values


def discover_github_repository(
    owner: str,
    repository: str,
) -> dict[str, str]:
    result = run_command(
        [
            "gh",
            "api",
            f"repos/{owner}/{repository}",
        ],
        capture_output=True,
    )

    try:
        payload = json.loads(
            result.stdout
        )
    except json.JSONDecodeError as exc:
        raise GitHubConfigurationError(
            "GitHub CLI returned invalid repository JSON."
        ) from exc

    try:
        discovered_owner = str(
            payload["owner"]["login"]
        )
        owner_id = str(
            payload["owner"]["id"]
        )
        discovered_repository = str(
            payload["name"]
        )
        repository_id = str(
            payload["id"]
        )
    except (KeyError, TypeError) as exc:
        raise GitHubConfigurationError(
            "GitHub repository response is missing immutable "
            "owner/repository identity fields."
        ) from exc

    if discovered_owner.lower() != owner.lower():
        raise GitHubConfigurationError(
            "Configured GitHub owner does not match the discovered owner."
        )

    if discovered_repository.lower() != repository.lower():
        raise GitHubConfigurationError(
            "Configured GitHub repository does not match the "
            "discovered repository."
        )

    print(
        "[PASS] GitHub repository discovered: "
        f"{discovered_owner}/{discovered_repository} "
        f"(owner ID {owner_id}, repository ID {repository_id})."
    )

    return {
        "owner": discovered_owner,
        "owner_id": owner_id,
        "repository": discovered_repository,
        "repository_id": repository_id,
    }


def terraform_bootstrap_outputs(
    bootstrap_dir: Path,
) -> dict[str, Any]:
    run_command(
        [
            "terraform",
            "init",
            "-reconfigure",
            "-backend-config=backend.hcl",
        ],
        cwd=bootstrap_dir,
    )

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
        outputs = json.loads(
            result.stdout
        )
    except json.JSONDecodeError as exc:
        raise GitHubConfigurationError(
            "Terraform returned invalid bootstrap output JSON."
        ) from exc

    if not isinstance(outputs, dict):
        raise GitHubConfigurationError(
            "Terraform returned an unexpected bootstrap output structure."
        )

    return outputs


def output_value(
    outputs: dict[str, Any],
    name: str,
) -> str:
    entry = outputs.get(
        name
    )

    if not isinstance(entry, dict):
        raise GitHubConfigurationError(
            f"Required Terraform output '{name}' is missing."
        )

    value = entry.get(
        "value"
    )

    if value in (
        None,
        "",
    ):
        raise GitHubConfigurationError(
            f"Required Terraform output '{name}' is empty."
        )

    return str(
        value
    )


def expected_oidc_subjects(
    github: dict[str, str],
) -> dict[str, str]:
    prefix = (
        f"repo:{github['owner']}@{github['owner_id']}/"
        f"{github['repository']}@{github['repository_id']}"
    )

    return {
        "github_plan_subject": (
            f"{prefix}:pull_request"
        ),
        "github_apply_subject": (
            f"{prefix}:environment:{LEVEL0_ENVIRONMENT}"
        ),
        "github_governance_subject": (
            f"{prefix}:environment:{GOVERNANCE_ENVIRONMENT}"
        ),
    }


def verify_oidc_subjects(
    outputs: dict[str, Any],
    github: dict[str, str],
) -> None:
    expected = expected_oidc_subjects(
        github
    )

    for output_name, expected_value in expected.items():
        actual_value = output_value(
            outputs,
            output_name,
        )

        if actual_value != expected_value:
            raise GitHubConfigurationError(
                f"OIDC subject mismatch for {output_name}.\n"
                f"Expected: {expected_value}\n"
                f"Actual:   {actual_value}"
            )

        print(
            f"[PASS] {output_name}"
        )

    print(
        "[PASS] All APF OIDC subjects match immutable GitHub identity."
    )


def desired_variables(
    *,
    tenant_id: str,
    subscription_id: str,
    outputs: dict[str, Any],
) -> dict[str, dict[str, str]]:
    return {
        "repository": {
            "AZURE_TENANT_ID": tenant_id,
            "AZURE_SUBSCRIPTION_ID": subscription_id,
            "AZURE_PLAN_CLIENT_ID": output_value(
                outputs,
                "plan_identity_client_id",
            ),
        },
        LEVEL0_ENVIRONMENT: {
            "AZURE_APPLY_CLIENT_ID": output_value(
                outputs,
                "apply_identity_client_id",
            ),
        },
        GOVERNANCE_ENVIRONMENT: {
            "AZURE_GOVERNANCE_CLIENT_ID": output_value(
                outputs,
                "governance_identity_client_id",
            ),
        },
    }


def environment_exists(
    repo_slug: str,
    environment_name: str,
) -> bool:
    result = run_command(
        [
            "gh",
            "api",
            f"repos/{repo_slug}/environments/{environment_name}",
            "--silent",
        ],
        capture_output=True,
        check=False,
    )

    if result.returncode == 0:
        return True

    combined = (
        (result.stdout or "")
        + "\n"
        + (result.stderr or "")
    )

    if (
        "404" in combined
        or "Not Found" in combined
    ):
        return False

    raise GitHubConfigurationError(
        "Unable to determine GitHub environment state for "
        f"'{environment_name}'.\n{combined.strip()}"
    )


def ensure_environment(
    repo_slug: str,
    environment_name: str,
) -> None:
    run_command(
        [
            "gh",
            "api",
            "-X",
            "PUT",
            f"repos/{repo_slug}/environments/{environment_name}",
            "--input",
            "-",
            "--silent",
        ],
        input_text="{}\n",
    )

    print(
        f"[PASS] GitHub environment '{environment_name}' configured."
    )


def list_variables(
    repo_slug: str,
    *,
    environment_name: str | None = None,
) -> dict[str, str]:
    command = [
        "gh",
        "variable",
        "list",
        "--repo",
        repo_slug,
        "--json",
        "name,value",
    ]

    if environment_name is not None:
        command.extend(
            [
                "--env",
                environment_name,
            ]
        )

    result = run_command(
        command,
        capture_output=True,
    )

    try:
        payload = json.loads(
            result.stdout
        )
    except json.JSONDecodeError as exc:
        raise GitHubConfigurationError(
            "GitHub CLI returned invalid variable JSON."
        ) from exc

    if not isinstance(payload, list):
        raise GitHubConfigurationError(
            "GitHub CLI returned an unexpected variable response."
        )

    values: dict[str, str] = {}

    for entry in payload:
        if not isinstance(entry, dict):
            continue

        name = entry.get(
            "name"
        )

        value = entry.get(
            "value"
        )

        if isinstance(name, str):
            values[name] = (
                str(value)
                if value is not None
                else ""
            )

    return values


def set_variable(
    repo_slug: str,
    name: str,
    value: str,
    *,
    environment_name: str | None = None,
) -> None:
    command = [
        "gh",
        "variable",
        "set",
        name,
        "--repo",
        repo_slug,
    ]

    if environment_name is not None:
        command.extend(
            [
                "--env",
                environment_name,
            ]
        )

    run_command(
        command,
        input_text=value,
    )


def plan_variable_changes(
    *,
    repo_slug: str,
    desired: dict[str, dict[str, str]],
    environment_state: dict[str, bool],
) -> tuple[list[str], dict[str, dict[str, str]]]:
    changes: list[str] = []

    current: dict[str, dict[str, str]] = {
        "repository": list_variables(
            repo_slug
        ),
    }

    for environment_name in (
        LEVEL0_ENVIRONMENT,
        GOVERNANCE_ENVIRONMENT,
    ):
        if environment_state[environment_name]:
            current[environment_name] = list_variables(
                repo_slug,
                environment_name=environment_name,
            )
        else:
            current[environment_name] = {}

    for scope, desired_values in desired.items():
        current_values = current[scope]

        for name, desired_value in desired_values.items():
            current_value = current_values.get(
                name
            )

            if current_value is None:
                changes.append(
                    f"{scope}: create {name}"
                )
            elif current_value != desired_value:
                changes.append(
                    f"{scope}: update {name}"
                )
            else:
                print(
                    f"[PASS] {scope}: {name}"
                )

    return (
        changes,
        current,
    )


def apply_variables(
    *,
    repo_slug: str,
    desired: dict[str, dict[str, str]],
) -> None:
    for name, value in desired["repository"].items():
        set_variable(
            repo_slug,
            name,
            value,
        )

        print(
            f"[PASS] repository: {name} configured."
        )

    for environment_name in (
        LEVEL0_ENVIRONMENT,
        GOVERNANCE_ENVIRONMENT,
    ):
        for name, value in desired[environment_name].items():
            set_variable(
                repo_slug,
                name,
                value,
                environment_name=environment_name,
            )

            print(
                f"[PASS] {environment_name}: {name} configured."
            )


def verify_final_configuration(
    *,
    repo_slug: str,
    desired: dict[str, dict[str, str]],
) -> None:
    current = {
        "repository": list_variables(
            repo_slug
        ),
        LEVEL0_ENVIRONMENT: list_variables(
            repo_slug,
            environment_name=LEVEL0_ENVIRONMENT,
        ),
        GOVERNANCE_ENVIRONMENT: list_variables(
            repo_slug,
            environment_name=GOVERNANCE_ENVIRONMENT,
        ),
    }

    for scope, desired_values in desired.items():
        current_values = current[scope]

        for name, expected_value in desired_values.items():
            actual_value = current_values.get(
                name
            )

            if actual_value != expected_value:
                raise GitHubConfigurationError(
                    f"GitHub variable verification failed for "
                    f"{scope}:{name}."
                )

    print(
        "[PASS] GitHub Actions variables match APF desired state."
    )


def print_plan(
    *,
    environment_state: dict[str, bool],
    variable_changes: list[str],
) -> None:
    print()
    print("GitHub configuration plan")
    print("-------------------------")

    changes = 0

    for environment_name, exists in environment_state.items():
        if exists:
            print(
                f"[PASS] environment: {environment_name}"
            )
        else:
            print(
                f"[PLAN] create environment: {environment_name}"
            )
            changes += 1

    for change in variable_changes:
        print(
            f"[PLAN] {change}"
        )
        changes += 1

    if changes == 0:
        print()
        print(
            "No changes. GitHub configuration matches APF desired state."
        )
    else:
        print()
        print(
            f"Planned GitHub configuration changes: {changes}"
        )


def main() -> int:
    args = parse_arguments()

    project_dir = args.project_dir.resolve()

    print(
        "Azure Platform Foundation GitHub configuration"
    )
    print(
        "----------------------------------------------"
    )
    print(f"Project: {project_dir}")
    print()

    try:
        require_command(
            "gh"
        )
        require_command(
            "terraform"
        )

        bootstrap_dir = verify_project_structure(
            project_dir
        )

        verify_workflow_contract(
            project_dir
        )

        (
            tenant_id,
            subscription_id,
            configured_owner,
            configured_repository,
        ) = load_customer_context(
            project_dir
        )

        print("Preflight checks...")
        verify_terraform_version()
        verify_github_authentication()

        github = discover_github_repository(
            configured_owner,
            configured_repository,
        )

        repo_slug = (
            f"{github['owner']}/"
            f"{github['repository']}"
        )

        print()
        print("Reading Level 0 bootstrap outputs...")

        outputs = terraform_bootstrap_outputs(
            bootstrap_dir
        )

        print()
        print("Validating APF OIDC subjects...")

        verify_oidc_subjects(
            outputs,
            github,
        )

        desired = desired_variables(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            outputs=outputs,
        )

        environment_state = {
            LEVEL0_ENVIRONMENT: environment_exists(
                repo_slug,
                LEVEL0_ENVIRONMENT,
            ),
            GOVERNANCE_ENVIRONMENT: environment_exists(
                repo_slug,
                GOVERNANCE_ENVIRONMENT,
            ),
        }

        (
            variable_changes,
            _,
        ) = plan_variable_changes(
            repo_slug=repo_slug,
            desired=desired,
            environment_state=environment_state,
        )

        print_plan(
            environment_state=environment_state,
            variable_changes=variable_changes,
        )

        if not args.apply:
            print()
            print(
                "No GitHub changes were applied."
            )
            print(
                "Run the same command with --apply to configure "
                "GitHub."
            )
            return 0

        print()
        print("Applying GitHub configuration...")

        for environment_name, exists in environment_state.items():
            if not exists:
                ensure_environment(
                    repo_slug,
                    environment_name,
                )

        apply_variables(
            repo_slug=repo_slug,
            desired=desired,
        )

        print()
        print("Verifying GitHub configuration...")

        verify_final_configuration(
            repo_slug=repo_slug,
            desired=desired,
        )

        final_environment_state = {
            LEVEL0_ENVIRONMENT: environment_exists(
                repo_slug,
                LEVEL0_ENVIRONMENT,
            ),
            GOVERNANCE_ENVIRONMENT: environment_exists(
                repo_slug,
                GOVERNANCE_ENVIRONMENT,
            ),
        }

        if not all(
            final_environment_state.values()
        ):
            raise GitHubConfigurationError(
                "One or more required GitHub environments are missing "
                "after apply."
            )

        print(
            "[PASS] Required GitHub environments exist."
        )

        print()
        print(
            "GitHub configuration completed successfully."
        )
        print()
        print(
            "Repository variables:"
        )
        print(
            "  AZURE_TENANT_ID"
        )
        print(
            "  AZURE_SUBSCRIPTION_ID"
        )
        print(
            "  AZURE_PLAN_CLIENT_ID"
        )
        print()
        print(
            f"Environment {LEVEL0_ENVIRONMENT}:"
        )
        print(
            "  AZURE_APPLY_CLIENT_ID"
        )
        print()
        print(
            f"Environment {GOVERNANCE_ENVIRONMENT}:"
        )
        print(
            "  AZURE_GOVERNANCE_CLIENT_ID"
        )

        return 0

    except GitHubConfigurationError as exc:
        print()
        print(
            f"[ERROR] {exc}",
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print()
        print(
            "[ERROR] GitHub configuration interrupted.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
