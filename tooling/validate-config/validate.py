#!/usr/bin/env python3

"""
Azure Platform Foundation configuration validator.

Validates APF YAML configuration files against their corresponding
JSON Schema definitions.

Usage:

    python validate.py \
        --config-dir ../../config/examples/greenfield-minimal \
        --schema-dir ../../config/schema
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


CONFIG_SCHEMA_MAP = {
    "foundation.yaml": "foundation.schema.json",
    "customer.yaml": "customer.schema.json",
    "platform.yaml": "platform.schema.json",
}


class ValidationFailure(Exception):
    """Raised when APF configuration validation cannot be completed."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Azure Platform Foundation configuration."
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        required=True,
        help="Directory containing APF YAML configuration files.",
    )

    parser.add_argument(
        "--schema-dir",
        type=Path,
        required=True,
        help="Directory containing APF JSON Schema files.",
    )

    return parser.parse_args()


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    except yaml.YAMLError as exc:
        raise ValidationFailure(
            f"Invalid YAML syntax in '{path}': {exc}"
        ) from exc

    except OSError as exc:
        raise ValidationFailure(
            f"Unable to read '{path}': {exc}"
        ) from exc


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as exc:
        raise ValidationFailure(
            f"Invalid JSON syntax in schema '{path}': {exc}"
        ) from exc

    except OSError as exc:
        raise ValidationFailure(
            f"Unable to read schema '{path}': {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValidationFailure(
            f"Schema '{path}' must contain a JSON object."
        )

    return data


def format_error_path(error) -> str:
    if not error.absolute_path:
        return "<root>"

    result = ""

    for part in error.absolute_path:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            if result:
                result += "."
            result += str(part)

    return result


def validate_document(
    config_path: Path,
    schema_path: Path,
) -> list[str]:

    config = load_yaml(config_path)
    schema = load_json(schema_path)

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValidationFailure(
            f"Invalid JSON Schema '{schema_path}': {exc.message}"
        ) from exc

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors = sorted(
        validator.iter_errors(config),
        key=lambda error: list(error.absolute_path),
    )

    formatted_errors: list[str] = []

    for error in errors:
        path = format_error_path(error)

        formatted_errors.append(
            f"{config_path.name}: {path}: {error.message}"
        )

    return formatted_errors


def main() -> int:
    args = parse_arguments()

    config_dir = args.config_dir.resolve()
    schema_dir = args.schema_dir.resolve()

    if not config_dir.is_dir():
        print(
            f"[ERROR] Configuration directory does not exist: {config_dir}",
            file=sys.stderr,
        )
        return 2

    if not schema_dir.is_dir():
        print(
            f"[ERROR] Schema directory does not exist: {schema_dir}",
            file=sys.stderr,
        )
        return 2

    validation_errors: list[str] = []

    print("Azure Platform Foundation configuration validation")
    print("--------------------------------------------------")

    for config_name, schema_name in CONFIG_SCHEMA_MAP.items():
        config_path = config_dir / config_name
        schema_path = schema_dir / schema_name

        if not config_path.is_file():
            validation_errors.append(
                f"{config_name}: required configuration file is missing"
            )
            print(f"[FAIL] {config_name}")
            continue

        if not schema_path.is_file():
            validation_errors.append(
                f"{schema_name}: required schema file is missing"
            )
            print(f"[FAIL] {config_name}")
            continue

        try:
            errors = validate_document(
                config_path=config_path,
                schema_path=schema_path,
            )
        except ValidationFailure as exc:
            validation_errors.append(str(exc))
            print(f"[FAIL] {config_name}")
            continue

        if errors:
            validation_errors.extend(errors)
            print(f"[FAIL] {config_name}")
        else:
            print(f"[PASS] {config_name}")

    print()

    if validation_errors:
        print("Validation failed:")
        print()

        for error in validation_errors:
            print(f"  - {error}")

        print()
        print(
            f"{len(validation_errors)} validation error(s) detected."
        )

        return 1

    print("Configuration is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())