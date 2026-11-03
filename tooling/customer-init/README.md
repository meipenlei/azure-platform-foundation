# APF Customer Initializer

The APF Customer Initializer creates a customer-specific Azure Platform
Foundation implementation project from validated APF configuration.

The initializer does not deploy Azure resources.

Its responsibility is limited to transforming a valid APF configuration
into a reproducible customer project structure.

## Process

```text
APF Configuration
       ↓
Schema Validation
       ↓
Customer Initializer
       ↓
Customer Project
       ↓
Level 0 Bootstrap
```

Configuration validation is mandatory.

The initializer uses the same APF configuration validator that is used
during local development and CI/CD validation.

## Installation

From the Azure Platform Foundation repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r tooling/customer-init/requirements.txt
```

## Generate the Minimal Greenfield Reference Project

Run:

```bash
python tooling/customer-init/init.py \
  --config-dir config/examples/greenfield-minimal \
  --output-dir /tmp/apf-lab-azure-platform
```

The initializer first validates:

```text
foundation.yaml
customer.yaml
platform.yaml
```

against the APF schemas.

If validation fails, project generation stops.

## Expected Output

A successful initialization creates a structure similar to:

```text
apf-lab-azure-platform/
│
├── .foundation/
│   └── metadata.yaml
│
├── config/
│   ├── foundation.yaml
│   ├── customer.yaml
│   └── platform.yaml
│
├── levels/
│   ├── level0/
│   ├── level1/
│   ├── level2/
│   ├── level3/
│   └── level4/
│
├── governance/
│   ├── policies/
│   ├── permissions/
│   └── exceptions/
│
├── landing-zones/
│   └── profiles/
│
├── execution/
│
├── docs/
│   └── decisions/
│
├── .gitignore
└── README.md
```

## Source of Truth

The authoritative customer configuration remains:

```text
config/foundation.yaml
config/customer.yaml
config/platform.yaml
```

Generated metadata must not duplicate authoritative platform
configuration.

## Safety

The initializer must never generate or request:

- Azure client secrets;
- passwords;
- Personal Access Tokens;
- private keys;
- long-lived deployment credentials.

Authentication and execution credentials are established during the
Level 0 bootstrap process using workload identity federation or other
supported short-lived mechanisms.

## Current Scope

Version 0.1 creates the customer project locally.

It does not currently:

- create a GitHub repository;
- create an Azure DevOps repository;
- authenticate against Azure;
- create Terraform state;
- create deployment identities;
- deploy Level 0.

Those capabilities are implemented in subsequent APF components.
