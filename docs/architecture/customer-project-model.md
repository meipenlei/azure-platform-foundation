# Azure Platform Foundation – Customer Project Model

**Version:** 0.1  
**Status:** Draft  
**Project:** Azure Platform Foundation

---

## 1. Purpose

This document defines how the reusable **Azure Platform Foundation (APF)** product is transformed into a customer-specific implementation.

The objective is to clearly separate:

- reusable platform product logic;
- customer-specific configuration;
- customer-specific extensions;
- execution-provider configuration;
- generated artifacts;
- secrets and sensitive information.

The Customer Project Model is a core part of the APF architecture.

It ensures that customer environments can evolve independently from the Foundation product without requiring permanent forks of the core repository.

---

# 2. Core Principle

Azure Platform Foundation consists of two distinct repository types:

```text
Product Repository
        │
        ▼
Customer Implementation Repository
```

The **Product Repository** contains reusable platform logic.

The **Customer Implementation Repository** contains customer-specific configuration and references to versioned Foundation components.

The product repository must not contain customer-specific operational data.

The customer repository must not duplicate the entire Foundation implementation unless explicitly required.

---

# 3. Product Repository

The main APF repository represents the reusable platform product.

Example:

```text
azure-platform-foundation
```

It contains:

- architecture documentation;
- configuration schemas;
- reusable Foundation modules;
- Level 0–4 implementation logic;
- governance baselines;
- policy definitions;
- permission models;
- platform profiles;
- customer initialization tooling;
- execution-provider adapters;
- AI agent definitions;
- tests;
- examples.

The Product Repository is versioned independently.

Example releases:

```text
v0.1.0
v0.2.0
v1.0.0
v1.1.0
```

Customer implementations should explicitly reference a defined Foundation version.

---

# 4. Customer Implementation Repository

Each customer or environment receives its own implementation repository.

Examples:

```text
contoso-azure-platform
fabrikam-azure-platform
customer-x-azure-platform
```

A Customer Implementation Repository represents the desired state of one customer platform.

It contains:

- customer metadata;
- Azure tenant and subscription references;
- selected Foundation version;
- enabled capabilities;
- environment-specific settings;
- policy profile selection;
- permission mappings;
- landing zone profiles;
- customer-specific extensions;
- approved exceptions;
- execution-provider configuration;
- customer architecture decisions.

The customer repository is the main source of truth for the customer implementation.

---

# 5. Separation of Responsibilities

The separation between product and customer repositories follows this model:

```text
Azure Platform Foundation
        │
        │ reusable logic
        │ modules
        │ schemas
        │ defaults
        │ governance baselines
        ▼
Customer Repository
        │
        │ customer configuration
        │ extensions
        │ exceptions
        │ environment metadata
        ▼
Azure Environment
```

The Foundation defines how the platform works.

The customer repository defines how the Foundation is configured for a specific customer.

---

# 6. Customer Initialization

A customer implementation is created through a standardized initialization process.

Conceptually:

```text
apf init
```

or:

```text
apf init --interactive
```

The initialization process collects the minimum information required to create a customer implementation.

Typical inputs include:

```text
Customer name
Customer identifier
Azure tenant
Bootstrap subscription
Primary Azure region
Deployment mode
Execution provider
Source-control organization
Repository name
Governance profile
Network profile
```

Example:

```yaml
customer:
  id: contoso
  display_name: Contoso GmbH

azure:
  tenant_id: "<tenant-id>"
  bootstrap_subscription_id: "<subscription-id>"
  primary_region: germanywestcentral

deployment:
  mode: greenfield

execution:
  provider: github

governance:
  profile: enterprise

network:
  topology: hub_spoke
```

---

# 7. Generated Customer Repository Structure

A generated customer repository may initially use the following structure:

```text
contoso-azure-platform/
│
├── .foundation/
│   ├── version.yaml
│   └── metadata.yaml
│
├── config/
│   ├── customer.yaml
│   ├── platform.yaml
│   ├── regions.yaml
│   └── features.yaml
│
├── levels/
│   ├── level0/
│   ├── level1/
│   ├── level2/
│   ├── level3/
│   └── level4/
│
├── governance/
│   ├── permissions/
│   ├── policies/
│   └── exceptions/
│
├── landing-zones/
│   └── profiles/
│
├── execution/
│   └── provider.yaml
│
├── docs/
│   ├── architecture.md
│   └── decisions/
│
└── README.md
```

This structure is intentionally configuration-focused.

Reusable implementation logic should remain in the Foundation product wherever possible.

---

# 8. Foundation Version Pinning

Every customer implementation must explicitly define the Foundation version it uses.

Example:

```yaml
foundation:
  version: "v0.3.0"
```

or, depending on the implementation mechanism:

```hcl
module "level0" {
  source = "github.com/meipenlei/azure-platform-foundation//foundation/levels/level0?ref=v0.3.0"
}
```

Version pinning ensures:

- reproducible deployments;
- controlled upgrades;
- customer-specific release planning;
- predictable behavior;
- rollback capability.

Customers must not automatically consume unreleased changes from the Foundation main branch.

---

# 9. Configuration Model

Customer customization should primarily be expressed through structured configuration.

Examples include:

```yaml
platform:
  environment_type: enterprise
  primary_region: germanywestcentral

governance:
  profile: enterprise

network:
  topology: hub_spoke

execution:
  provider: github
```

The Foundation translates these higher-level decisions into the required infrastructure implementation.

The customer should not need to configure every underlying Terraform variable directly.

The configuration model therefore acts as an abstraction layer between the customer and the underlying IaC implementation.

---

# 10. Customer Extensions

Customer-specific requirements are supported through controlled extension points.

Examples include:

- additional policies;
- custom policy initiatives;
- custom role definitions;
- naming exceptions;
- additional network rules;
- additional landing zone profiles;
- customer-specific platform services;
- environment-specific integrations.

Extensions must be explicitly isolated from reusable Foundation logic.

An extension should not require modification of the core product unless it represents a reusable capability that should become part of APF itself.

---

# 11. Customer Exceptions

Some customer requirements may intentionally deviate from Foundation defaults.

These deviations must be documented as exceptions.

Example:

```yaml
exceptions:
  - id: EX-001
    type: policy
    control: deny-public-ip
    scope: workload-subscription
    reason: "Legacy vendor dependency"
    approved_by: security
    expires: 2027-03-31
```

Exceptions should include:

- identifier;
- affected control;
- scope;
- reason;
- owner;
- approval;
- expiration date where applicable.

Exceptions are part of the managed platform state.

They must not exist as undocumented manual changes.

---

# 12. Greenfield Customer Project Lifecycle

A Greenfield customer implementation follows this lifecycle:

```text
Customer Definition
        ↓
Repository Generation
        ↓
Bootstrap Validation
        ↓
Level 0 Deployment
        ↓
Platform Handover
        ↓
Level 1–4 Deployment
        ↓
Ongoing Platform Operations
```

The initial implementation may start with only:

```text
Tenant
Subscription
Source Control
Bootstrap Identity
```

After Level 0, the platform should be able to manage further changes through its own execution plane.

---

# 13. Brownfield Customer Project Lifecycle

A Brownfield customer implementation follows a different lifecycle:

```text
Customer Definition
        ↓
Environment Discovery
        ↓
Assessment
        ↓
Gap Analysis
        ↓
Adoption Configuration
        ↓
Controlled Integration
        ↓
Managed Platform
```

Brownfield customer repositories may initially contain discovery outputs and adoption decisions in addition to target configuration.

Example:

```text
discovery/
assessment/
adoption/
exceptions/
```

The Foundation must never assume that existing resources can be replaced without explicit approval.

---

# 14. Execution Provider Abstraction

The customer implementation selects an execution provider.

Initial providers are:

```text
github
azure-devops
```

Example:

```yaml
execution:
  provider: github
```

Provider-specific implementation details must remain separated from the Foundation platform model.

The customer configuration expresses the provider choice.

The Foundation maps that choice to the corresponding pipeline adapter.

---

# 15. Sensitive Data

The customer repository may contain identifiers and configuration that are specific to the customer.

It must not contain:

- passwords;
- client secrets;
- private keys;
- long-lived access tokens;
- unprotected credentials;
- confidential runtime secrets.

Sensitive runtime values must be stored in appropriate secret-management or identity systems.

Examples include:

- workload identity federation;
- managed identities;
- GitHub environments and secrets;
- Azure DevOps service connections;
- Azure Key Vault.

The Product Repository must never contain real customer secrets or customer-specific confidential configuration.

---

# 16. Bootstrap Data

Bootstrap configuration may include customer-specific identifiers such as:

```text
tenant_id
subscription_id
organization_name
repository_name
region
```

These values belong in the customer implementation repository.

They must never be hard-coded into the reusable Foundation product.

---

# 17. Upgrade Model

Foundation upgrades are explicit customer operations.

Example:

```text
Current:
v0.3.0

Target:
v0.4.0
```

The upgrade process should include:

```text
Release Notes
      ↓
Compatibility Check
      ↓
Configuration Validation
      ↓
Terraform Plan
      ↓
Review
      ↓
Approval
      ↓
Apply
```

Major behavior changes should not silently affect customer environments.

---

# 18. Customer Repository Ownership

The customer implementation repository should have clearly defined ownership.

Typical owners may include:

```text
Platform Team
Cloud Engineering
Security Engineering
Customer Operations
```

Repository permissions should reflect platform responsibilities.

Direct modification of protected branches should be restricted.

Changes should preferably follow pull-request-based workflows.

---

# 19. Generated vs. Maintained Files

Files in the customer repository fall into three categories.

## Generated

Created by APF initialization tooling.

Examples:

```text
.foundation/version.yaml
config/customer.yaml
config/platform.yaml
execution/provider.yaml
```

## Customer Maintained

Expected to be modified by the customer.

Examples:

```text
governance/exceptions/
governance/permissions/
landing-zones/profiles/
docs/decisions/
```

## Foundation Managed

Generated or updated based on the Foundation version.

These files should not normally be edited manually.

If generated files require customization, the customization must happen through supported extension points.

---

# 20. Customer Project Invariants

Every customer implementation must preserve the following invariants:

1. The Foundation version is explicitly defined.
2. Customer-specific data does not enter the Product Repository.
3. Secrets are not committed to source control.
4. Platform changes remain declarative.
5. Manual changes do not become the authoritative desired state.
6. Customer extensions are isolated from reusable Foundation logic.
7. Customer exceptions are documented.
8. CI/CD provider details remain separated from the platform model.
9. Platform upgrades are explicit and reviewable.
10. The customer repository remains the source of truth for that implementation.

---

# 21. Initial Greenfield Target

For the first APF implementation, the Customer Project Model must support the following scenario:

```text
One Microsoft Entra tenant
+
One Azure subscription
+
GitHub or Azure DevOps
+
One bootstrap identity
```

From this starting point, APF must be able to generate a customer implementation that can deploy Level 0.

The expected result is:

```text
Customer Repository
        +
Customer Configuration
        +
Terraform Remote State
        +
Deployment Identities
        +
OIDC / Workload Identity Federation
        +
CI/CD Pipeline
        +
Operational Level 0
```

This scenario defines the first reference implementation of the Customer Project Model.

---

# 22. Example End-to-End Flow

A future customer initialization flow may look like:

```text
$ apf init
```

The tool collects customer information.

Example:

```text
Customer name: Contoso
Customer ID: contoso
Deployment mode: Greenfield
Azure region: Germany West Central
Execution provider: GitHub
Governance profile: Enterprise
Network profile: Hub-Spoke
```

APF generates:

```text
contoso-azure-platform/
```

The generated project contains:

```text
Foundation version
Customer configuration
Platform configuration
Execution provider configuration
Initial Level 0 configuration
Documentation
```

The first deployment then follows:

```text
Bootstrap authentication
        ↓
Terraform initialization
        ↓
Level 0 plan
        ↓
Review
        ↓
Level 0 apply
        ↓
OIDC-enabled execution plane
        ↓
Bootstrap handover
```

From that point onward, normal platform changes are performed through Git and the execution pipeline.

---

# 23. Design Goal

The long-term design goal is that creating a customer platform should feel like configuring a product rather than copying a Terraform repository.

The target experience is:

```text
Select
Configure
Validate
Deploy
Operate
Upgrade
```

not:

```text
Fork
Search
Replace
Patch
Hope
```

This distinction is fundamental to Azure Platform Foundation.

---

# 24. Closing Principle

The reusable Foundation and the customer implementation are intentionally separated.

The Foundation defines:

> **How the platform works.**

The customer project defines:

> **How the platform is configured for this customer.**

The resulting Azure environment is the controlled realization of both.