#!/usr/bin/env python3

"""
Azure Platform Foundation customer project initializer.

Creates a customer-specific APF implementation project from a validated
Foundation configuration.

Current implementation:
- validates the APF configuration
- creates the customer repository structure
- copies the authoritative configuration files
- discovers immutable GitHub owner/repository IDs
- writes APF discovery metadata
- generates the Level 0 bootstrap Terraform root
- generates the Level 0 governance Terraform root
- generates deterministic Terraform bootstrap input values

Example:

    python tooling/customer-init/init.py \
        --config-dir config/examples/greenfield-minimal \
        --output-dir /tmp/apf-lab-azure-platform
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


# ---------------------------------------------------------------------------
# APF toolchain defaults
# ---------------------------------------------------------------------------

TERRAFORM_VERSION = "1.17.1"
TERRAFORM_REQUIRED_VERSION = "~> 1.17"
AZURERM_VERSION = "4.81.0"

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

CONFIG_FILES = (
    "foundation.yaml",
    "customer.yaml",
    "platform.yaml",
)


# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize an Azure Platform Foundation customer project."
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        required=True,
        help="Directory containing the APF configuration files.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where the customer project will be created.",
    )

    parser.add_argument(
        "--schema-dir",
        type=Path,
        required=False,
        help="Optional APF schema directory. Defaults to config/schema.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Configuration loading and validation
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(
            f"Unable to read configuration '{path}': {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Configuration '{path}' must contain a YAML object."
        )

    return data


def validate_configuration(
    repo_root: Path,
    config_dir: Path,
    schema_dir: Path,
) -> int:
    validator = repo_root / "tooling" / "validate-config" / "validate.py"

    if not validator.is_file():
        print(
            f"[ERROR] APF validator not found: {validator}",
            file=sys.stderr,
        )
        return 2

    print("Validating source configuration...")
    print()

    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            "--config-dir",
            str(config_dir),
            "--schema-dir",
            str(schema_dir),
        ],
        check=False,
    )

    return result.returncode


# ---------------------------------------------------------------------------
# Jinja template handling
# ---------------------------------------------------------------------------

def create_template_environment() -> Environment:
    """
    Create the Jinja environment used for generated customer files.

    [[ ... ]] is deliberately used instead of Jinja's default delimiters so
    future GitHub Actions templates can safely contain GitHub expressions.
    """

    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=StrictUndefined,
        variable_start_string="[[",
        variable_end_string="]]",
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_template(
    environment: Environment,
    template_name: str,
    target: Path,
    context: dict[str, Any],
) -> None:
    template = environment.get_template(template_name)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        template.render(**context),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# GitHub discovery
# ---------------------------------------------------------------------------

def discover_github_repository(
    owner: str,
    repository: str,
) -> dict[str, str]:
    """
    Resolve immutable GitHub owner and repository IDs.

    The target repository must already exist because APF uses its immutable
    owner/repository IDs when constructing GitHub OIDC federation subjects.
    """

    if shutil.which("gh") is None:
        raise RuntimeError(
            "GitHub CLI 'gh' was not found. "
            "Install GitHub CLI and authenticate with 'gh auth login'."
        )

    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{owner}/{repository}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        error_message = result.stderr.strip()

        raise RuntimeError(
            f"Unable to discover GitHub repository '{owner}/{repository}'. "
            "Verify that the repository exists and that 'gh' is "
            f"authenticated.\n{error_message}"
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GitHub CLI returned an invalid JSON response."
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            "GitHub CLI returned an unexpected repository response."
        )

    try:
        owner_login = payload["owner"]["login"]
        owner_id = payload["owner"]["id"]
        repository_name = payload["name"]
        repository_id = payload["id"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            "GitHub repository response does not contain the "
            "required immutable identity fields."
        ) from exc

    return {
        "owner": str(owner_login),
        "owner_id": str(owner_id),
        "repository": str(repository_name),
        "repository_id": str(repository_id),
    }


# ---------------------------------------------------------------------------
# Output directory and repository structure
# ---------------------------------------------------------------------------

def ensure_output_directory_available(
    output_dir: Path,
) -> None:
    """
    Refuse to overwrite an existing non-empty customer project.
    """

    if output_dir.exists():
        if not output_dir.is_dir():
            raise RuntimeError(
                f"Output path exists and is not a directory: {output_dir}"
            )

        if any(output_dir.iterdir()):
            raise RuntimeError(
                f"Output directory is not empty: {output_dir}"
            )
    else:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )


def create_directory_structure(
    output_dir: Path,
) -> None:
    directories = (
        ".foundation",
        "config",
        "levels/level0",
        "levels/level1",
        "levels/level2",
        "levels/level3",
        "levels/level4",
        "governance/policies",
        "governance/permissions",
        "governance/exceptions",
        "landing-zones/profiles",
        "execution",
        "docs/decisions",
    )

    for directory in directories:
        path = output_dir / directory

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        if directory not in (
            ".foundation",
            "config",
        ):
            (path / ".gitkeep").touch()


# ---------------------------------------------------------------------------
# Customer configuration
# ---------------------------------------------------------------------------

def copy_configuration(
    config_dir: Path,
    output_dir: Path,
) -> None:
    target_config_dir = output_dir / "config"

    for filename in CONFIG_FILES:
        source = config_dir / filename
        target = target_config_dir / filename

        shutil.copy2(
            source,
            target,
        )


# ---------------------------------------------------------------------------
# APF metadata
# ---------------------------------------------------------------------------

def write_discovery_file(
    output_dir: Path,
    github: dict[str, str],
) -> None:
    """
    Write generated infrastructure discovery information.

    discovery.yaml is generated metadata, not customer intent.
    """

    discovery = {
        "schema_version": "0.1",
        "github": github,
    }

    target = output_dir / ".foundation" / "discovery.yaml"

    with target.open(
        "w",
        encoding="utf-8",
    ) as handle:
        yaml.safe_dump(
            discovery,
            handle,
            sort_keys=False,
        )


def write_metadata(
    output_dir: Path,
    customer: dict[str, Any],
) -> None:
    metadata = {
        "schema_version": "0.1",
        "generator": "apf-customer-init",
        "customer_id": customer["customer"]["id"],
        "configuration": {
            "foundation": "config/foundation.yaml",
            "customer": "config/customer.yaml",
            "platform": "config/platform.yaml",
        },
        "generated": {
            "discovery": ".foundation/discovery.yaml",
            "level0_bootstrap": "levels/level0/bootstrap",
            "level0_governance": "levels/level0/governance",
            "github_workflows": ".github/workflows",
        },
    }

    metadata_path = output_dir / ".foundation" / "metadata.yaml"

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        yaml.safe_dump(
            metadata,
            file,
            sort_keys=False,
        )


# ---------------------------------------------------------------------------
# Level 0 bootstrap generation
# ---------------------------------------------------------------------------

def render_level0_bootstrap(
    output_dir: Path,
    foundation_config: dict[str, Any],
    customer_config: dict[str, Any],
    platform_config: dict[str, Any],
    github: dict[str, str],
) -> None:
    """
    Generate the Level 0 bootstrap Terraform root.

    The initial bootstrap intentionally has no AzureRM backend configuration.
    Terraform therefore starts with local state.

    A later APF bootstrap lifecycle tool will execute the bootstrap, create
    the Azure state backend, generate backend configuration and migrate the
    local bootstrap state to Azure.
    """

    environment = create_template_environment()

    target_dir = output_dir / "levels" / "level0" / "bootstrap"

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    level0_gitkeep = output_dir / "levels" / "level0" / ".gitkeep"

    if level0_gitkeep.exists():
        level0_gitkeep.unlink()

    context = {
        "foundation_ref": foundation_config["foundation"]["version"],
        "terraform_version": TERRAFORM_VERSION,
        "terraform_required_version": TERRAFORM_REQUIRED_VERSION,
        "azurerm_version": AZURERM_VERSION,
    }

    templates = {
        "level0/bootstrap/versions.tf.j2": "versions.tf",
        "level0/bootstrap/providers.tf.j2": "providers.tf",
        "level0/bootstrap/variables.tf.j2": "variables.tf",
        "level0/bootstrap/main.tf.j2": "main.tf",
        "level0/bootstrap/outputs.tf.j2": "outputs.tf",
    }

    for template_name, target_name in templates.items():
        render_template(
            environment=environment,
            template_name=template_name,
            target=target_dir / target_name,
            context=context,
        )

    tfvars = {
        "tenant_id": customer_config["azure"]["tenant_id"],
        "subscription_id": customer_config["azure"]["bootstrap_subscription_id"],
        "location": customer_config["azure"]["primary_region"],
        "name_prefix": platform_config["naming"]["prefix"],
        "github_owner": github["owner"],
        "github_owner_id": github["owner_id"],
        "github_repository": github["repository"],
        "github_repository_id": github["repository_id"],
        "github_apply_environment": "apf-level0",
        "github_governance_environment": "apf-governance",
        "tags": {
            "environment": customer_config["customer"]["id"],
            "project": "azure-platform-foundation",
        },
    }

    tfvars_path = target_dir / "generated.auto.tfvars.json"

    with tfvars_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            tfvars,
            handle,
            indent=2,
        )
        handle.write("\n")


# ---------------------------------------------------------------------------
# Level 0 governance generation
# ---------------------------------------------------------------------------

def render_level0_governance(
    output_dir: Path,
    foundation_config: dict[str, Any],
) -> None:
    """
    Generate the Level 0 governance Terraform root.

    backend.tf is generated immediately.

    backend.hcl is intentionally not generated yet because the Azure state
    backend does not exist during initial customer project creation.

    A later APF bootstrap lifecycle tool will generate backend.hcl and provide
    the bootstrap-derived Terraform inputs required by governance.
    """

    environment = create_template_environment()

    target_dir = output_dir / "levels" / "level0" / "governance"

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    context = {
        "foundation_ref": foundation_config["foundation"]["version"],
        "terraform_version": TERRAFORM_VERSION,
        "terraform_required_version": TERRAFORM_REQUIRED_VERSION,
        "azurerm_version": AZURERM_VERSION,
    }

    templates = {
        "level0/governance/versions.tf.j2": "versions.tf",
        "level0/governance/providers.tf.j2": "providers.tf",
        "level0/governance/backend.tf.j2": "backend.tf",
        "level0/governance/variables.tf.j2": "variables.tf",
        "level0/governance/main.tf.j2": "main.tf",
        "level0/governance/outputs.tf.j2": "outputs.tf",
    }

    for template_name, target_name in templates.items():
        render_template(
            environment=environment,
            template_name=template_name,
            target=target_dir / target_name,
            context=context,
        )


# ---------------------------------------------------------------------------
# GitHub workflow generation
# ---------------------------------------------------------------------------

def render_github_workflows(
    output_dir: Path,
) -> None:
    """
    Generate the GitHub Actions workflows used by the APF Level 0
    execution and governance planes.

    The workflows are generated during customer initialization, but they
    become operational only after the later bootstrap lifecycle has created
    the Azure backend, configured GitHub environments and populated the
    required GitHub Actions configuration.
    """

    environment = create_template_environment()

    target_dir = output_dir / ".github" / "workflows"

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    context = {
        "terraform_version": TERRAFORM_VERSION,
    }

    templates = {
        "github/terraform-plan.yml.j2": "terraform-plan.yml",
        "github/terraform-apply.yml.j2": "terraform-apply.yml",
        "github/terraform-governance-plan.yml.j2": (
            "terraform-governance-plan.yml"
        ),
        "github/terraform-governance-apply.yml.j2": (
            "terraform-governance-apply.yml"
        ),
    }

    for template_name, target_name in templates.items():
        render_template(
            environment=environment,
            template_name=template_name,
            target=target_dir / target_name,
            context=context,
        )


# ---------------------------------------------------------------------------
# Repository support files
# ---------------------------------------------------------------------------

def write_gitignore(
    output_dir: Path,
) -> None:
    content = """\
# Terraform
.terraform/
*.tfstate
*.tfstate.*
*.tfplan

# Local Terraform variable files
*.tfvars
*.tfvars.json
*.auto.tfvars
*.auto.tfvars.json

# APF generated Terraform inputs are intentionally version controlled
!**/generated.auto.tfvars.json

crash.log
crash.*.log

# Secrets and local environment
.env
.env.*
!.env.example

# Python
.venv/
venv/
__pycache__/
*.py[cod]

# IDE
.vscode/
.idea/

# Operating system
.DS_Store

# Temporary files
*.tmp
*.bak
"""

    (output_dir / ".gitignore").write_text(
        content,
        encoding="utf-8",
    )


def write_readme(
    output_dir: Path,
    foundation: dict[str, Any],
    customer: dict[str, Any],
    platform: dict[str, Any],
) -> None:
    customer_id = customer["customer"]["id"]
    display_name = customer["customer"]["display_name"]
    foundation_version = foundation["foundation"]["version"]
    deployment_mode = platform["deployment"]["mode"]
    execution_provider = platform["execution"]["provider"]
    primary_region = customer["azure"]["primary_region"]

    # Deliberately avoid Markdown fenced code blocks here so this Python file
    # remains easy to copy, render and maintain.
    content = f"""\
# {display_name} Azure Platform

This repository contains the customer-specific implementation of the
**Azure Platform Foundation (APF)**.

## Platform Information

| Property | Value |
| --- | --- |
| Customer ID | `{customer_id}` |
| Foundation Version | `{foundation_version}` |
| Deployment Mode | `{deployment_mode}` |
| Primary Azure Region | `{primary_region}` |
| Execution Provider | `{execution_provider}` |

## Configuration

The authoritative platform configuration is stored in:

    config/
    ├── foundation.yaml
    ├── customer.yaml
    └── platform.yaml

These files define the customer-specific contract with Azure Platform
Foundation.

Generated implementation metadata is stored in:

    .foundation/
    ├── metadata.yaml
    └── discovery.yaml

`.foundation/discovery.yaml` contains generated infrastructure identity
information such as immutable GitHub owner and repository IDs.

It is generated by APF and should not be edited manually.

## Foundation Levels

    levels/
    ├── level0/
    │   ├── bootstrap/
    │   └── governance/
    ├── level1/
    ├── level2/
    ├── level3/
    └── level4/

## Level 0 Bootstrap

The Level 0 bootstrap root is generated from the authoritative APF
configuration.

Generated Terraform input values are stored in:

    levels/level0/bootstrap/generated.auto.tfvars.json

The initial Level 0 bootstrap starts with local Terraform state.

The APF bootstrap lifecycle will later create the Azure state backend
and migrate the bootstrap state to Azure.

## Level 0 Governance

The Level 0 governance root is generated automatically.

It manages privileged platform permissions separately from the normal
platform execution plane.

The initial governance root contains:

    levels/level0/governance/
    ├── backend.tf
    ├── main.tf
    ├── outputs.tf
    ├── providers.tf
    ├── variables.tf
    └── versions.tf

`backend.hcl` is intentionally not created during customer
initialization.

It will be generated later by the APF bootstrap lifecycle after the
Azure state backend exists.

## GitHub Workflows

The customer project contains generated GitHub Actions workflows:

    .github/workflows/
    ├── terraform-plan.yml
    ├── terraform-apply.yml
    ├── terraform-governance-plan.yml
    └── terraform-governance-apply.yml

These workflows use workload identity federation and do not require
long-lived Azure client secrets.

They become operational after the APF bootstrap lifecycle has configured
the Azure backend and the required GitHub environments and identifiers.

## Important

This repository contains customer-specific platform configuration.

Do not commit passwords, client secrets, private keys, access tokens,
or other long-lived credentials.

Platform authentication should use workload identity federation,
OIDC, managed identities, and other short-lived authentication
mechanisms supported by Azure Platform Foundation.
"""

    (output_dir / "README.md").write_text(
        content,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def print_summary(
    output_dir: Path,
    foundation: dict[str, Any],
    customer: dict[str, Any],
    platform: dict[str, Any],
    github: dict[str, str],
) -> None:
    print()
    print("Customer project initialized successfully.")
    print("------------------------------------------")

    print(f"Customer:        {customer['customer']['display_name']}")
    print(f"Customer ID:     {customer['customer']['id']}")
    print(f"Foundation:      {foundation['foundation']['version']}")
    print(f"Deployment mode: {platform['deployment']['mode']}")
    print(f"Execution:       {platform['execution']['provider']}")
    print(f"GitHub:          {github['owner']}/{github['repository']}")
    print(f"GitHub repo ID:  {github['repository_id']}")
    print(f"Terraform:       {TERRAFORM_VERSION}")
    print(f"AzureRM:         {AZURERM_VERSION}")
    print(f"Output:          {output_dir}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_arguments()

    repo_root = Path(__file__).resolve().parents[2]
    config_dir = args.config_dir.resolve()

    schema_dir = (
        args.schema_dir.resolve()
        if args.schema_dir
        else repo_root / "config" / "schema"
    )

    output_dir = args.output_dir.resolve()

    if not config_dir.is_dir():
        print(
            f"[ERROR] Configuration directory does not exist: {config_dir}",
            file=sys.stderr,
        )
        return 2

    validation_result = validate_configuration(
        repo_root=repo_root,
        config_dir=config_dir,
        schema_dir=schema_dir,
    )

    if validation_result != 0:
        print()
        print(
            "[ERROR] Customer project initialization aborted "
            "because configuration validation failed.",
            file=sys.stderr,
        )
        return validation_result

    try:
        foundation = load_yaml(
            config_dir / "foundation.yaml"
        )

        customer = load_yaml(
            config_dir / "customer.yaml"
        )

        platform = load_yaml(
            config_dir / "platform.yaml"
        )

        execution_provider = platform["execution"]["provider"]

        if execution_provider != "github":
            raise RuntimeError(
                "Level 0 customer root generation currently "
                "supports execution.provider='github' only."
            )

        github_config = platform["execution"].get("github")

        if not isinstance(github_config, dict):
            raise RuntimeError(
                "GitHub execution configuration is missing."
            )

        github_owner = github_config.get("owner")
        github_repository = github_config.get("repository")

        if not github_owner:
            raise RuntimeError(
                "execution.github.owner is missing."
            )

        if not github_repository:
            raise RuntimeError(
                "execution.github.repository is missing."
            )

        print()
        print(
            "Discovering immutable GitHub repository identity..."
        )

        github = discover_github_repository(
            owner=str(github_owner),
            repository=str(github_repository),
        )

        print(
            f"GitHub repository discovered: "
            f"{github['owner']}/{github['repository']} "
            f"(repository ID: {github['repository_id']})"
        )

        ensure_output_directory_available(
            output_dir
        )

        create_directory_structure(
            output_dir
        )

        copy_configuration(
            config_dir=config_dir,
            output_dir=output_dir,
        )

        write_metadata(
            output_dir=output_dir,
            customer=customer,
        )

        write_discovery_file(
            output_dir=output_dir,
            github=github,
        )

        print()
        print(
            "Generating Level 0 bootstrap Terraform root..."
        )

        render_level0_bootstrap(
            output_dir=output_dir,
            foundation_config=foundation,
            customer_config=customer,
            platform_config=platform,
            github=github,
        )

        print(
            "Generating Level 0 governance Terraform root..."
        )

        render_level0_governance(
            output_dir=output_dir,
            foundation_config=foundation,
        )

        print(
            "Generating GitHub Actions workflows..."
        )

        render_github_workflows(
            output_dir=output_dir,
        )

        write_gitignore(
            output_dir
        )

        write_readme(
            output_dir=output_dir,
            foundation=foundation,
            customer=customer,
            platform=platform,
        )

    except (
        KeyError,
        RuntimeError,
        OSError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        print(
            f"[ERROR] Customer project initialization failed: {exc}",
            file=sys.stderr,
        )
        return 2

    print_summary(
        output_dir=output_dir,
        foundation=foundation,
        customer=customer,
        platform=platform,
        github=github,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
