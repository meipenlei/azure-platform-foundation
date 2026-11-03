#!/usr/bin/env python3

"""
Azure Platform Foundation customer project initializer.

Creates a customer-specific APF implementation project from a validated
Foundation configuration.

Example:

    python tooling/customer-init/init.py \
        --config-dir config/examples/greenfield-minimal \
        --output-dir /tmp/apf-lab-azure-platform
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


CONFIG_FILES = (
    "foundation.yaml",
    "customer.yaml",
    "platform.yaml",
)


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

    validator = (
        repo_root
        / "tooling"
        / "validate-config"
        / "validate.py"
    )

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


def ensure_output_directory_available(output_dir: Path) -> None:
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
        output_dir.mkdir(parents=True)


def create_directory_structure(output_dir: Path) -> None:
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
        path.mkdir(parents=True, exist_ok=True)

        if directory not in (
            ".foundation",
            "config",
        ):
            (path / ".gitkeep").touch()


def copy_configuration(
    config_dir: Path,
    output_dir: Path,
) -> None:

    target_config_dir = output_dir / "config"

    for filename in CONFIG_FILES:
        source = config_dir / filename
        target = target_config_dir / filename

        shutil.copy2(source, target)


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
    }

    metadata_path = (
        output_dir
        / ".foundation"
        / "metadata.yaml"
    )

    with metadata_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            metadata,
            file,
            sort_keys=False,
        )


def write_gitignore(output_dir: Path) -> None:
    content = """\
# Terraform
.terraform/
*.tfstate
*.tfstate.*
*.tfplan
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

```text
config/
├── foundation.yaml
├── customer.yaml
└── platform.yaml
```

These files define the customer-specific contract with Azure Platform
Foundation.

## Foundation Levels

```text
levels/
├── level0/
├── level1/
├── level2/
├── level3/
└── level4/
```

The initial implementation target is **Level 0 – Bootstrap and Platform
Control Plane**.

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


def print_summary(
    output_dir: Path,
    foundation: dict[str, Any],
    customer: dict[str, Any],
    platform: dict[str, Any],
) -> None:

    print()
    print("Customer project initialized successfully.")
    print("------------------------------------------")
    print(
        f"Customer:        "
        f"{customer['customer']['display_name']}"
    )
    print(
        f"Customer ID:     "
        f"{customer['customer']['id']}"
    )
    print(
        f"Foundation:      "
        f"{foundation['foundation']['version']}"
    )
    print(
        f"Deployment mode: "
        f"{platform['deployment']['mode']}"
    )
    print(
        f"Execution:       "
        f"{platform['execution']['provider']}"
    )
    print(
        f"Output:          "
        f"{output_dir}"
    )


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
            f"[ERROR] Configuration directory does not exist: "
            f"{config_dir}",
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

        ensure_output_directory_available(output_dir)

        create_directory_structure(output_dir)

        copy_configuration(
            config_dir=config_dir,
            output_dir=output_dir,
        )

        write_metadata(
            output_dir=output_dir,
            customer=customer,
        )

        write_gitignore(output_dir)

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
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())