# Minimal Greenfield Example

This directory contains the minimal Azure Platform Foundation configuration required to describe a Greenfield Level 0 deployment.

The example is intended for documentation, schema validation, testing, and customer project initialization.

It does **not** contain deployable customer credentials or real Azure identifiers.

## Files

### `foundation.yaml`

Defines the Azure Platform Foundation version used by the customer implementation.

### `customer.yaml`

Defines customer metadata and the Azure target context.

The example uses placeholder UUIDs for the Microsoft Entra tenant and Azure subscription.

### `platform.yaml`

Defines the initial platform operating model.

The minimal example uses:

- Greenfield deployment mode
- Terraform
- GitHub Actions
- Workload Identity Federation
- No long-lived Azure deployment credentials

## Intended Flow

```text
foundation.yaml
customer.yaml
platform.yaml
       │
       ▼
Schema Validation
       │
       ▼
Customer Project Initialization
       │
       ▼
Level 0 Bootstrap
```

These files represent the initial contract between a customer implementation and Azure Platform Foundation.