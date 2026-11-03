# APF Configuration Validator

The APF Configuration Validator verifies Azure Platform Foundation customer configuration against the supported JSON Schema definitions.

The same validator is intended to be used:

- during local development;
- during customer project initialization;
- in GitHub Actions;
- in Azure DevOps Pipelines;
- by future AI Platform Engineering workflows.

## Supported Configuration

The initial validator expects:

```text
foundation.yaml
customer.yaml
platform.yaml
```

Each configuration file is validated against its corresponding schema:

```text
foundation.yaml
    ↓
foundation.schema.json

customer.yaml
    ↓
customer.schema.json

platform.yaml
    ↓
platform.schema.json
```

## Installation

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r tooling/validate-config/requirements.txt
```

## Validate the Minimal Greenfield Example

Run from the repository root:

```bash
python tooling/validate-config/validate.py \
  --config-dir config/examples/greenfield-minimal \
  --schema-dir config/schema
```

A successful validation returns:

```text
Azure Platform Foundation configuration validation
--------------------------------------------------
[PASS] foundation.yaml
[PASS] customer.yaml
[PASS] platform.yaml

Configuration is valid.
```

The process exits with status code `0`.

## Validation Failure

Invalid configuration produces a non-zero exit code.

Example:

```yaml
security:
  authentication: workload-identity-federation
  allow_long_lived_credentials: true
```

Because Azure Platform Foundation currently prohibits long-lived Azure deployment credentials, validation fails.

Example result:

```text
[FAIL] platform.yaml

Validation failed:

  - platform.yaml: security.allow_long_lived_credentials: False was expected
```

The process exits with status code `1`.

This makes the validator suitable for use as a CI/CD quality gate.

## Exit Codes

|Code|Meaning|
|---|---|
|0|Configuration is valid|
|1|Configuration violates an APF schema|
|2|Validation could not be performed|

## Design Principle

Configuration validation is a deterministic platform control.

Human users and AI agents may create or modify APF configuration, but configuration must pass schema validation before it can be processed by the Foundation.

```text
Human / AI Agent
       ↓
APF Configuration
       ↓
Schema Validation
       ↓
Valid?
  │          │
 Yes         No
  │          └── Reject
  ↓
Continue
```
