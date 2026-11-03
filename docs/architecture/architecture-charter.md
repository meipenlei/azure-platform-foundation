# Azure Platform Foundation – Architecture Charter

**Version:** 0.1  
**Status:** Draft  
**Project:** Azure Platform Foundation

---

## 1. Purpose

The **Azure Platform Foundation (APF)** is an opinionated but extensible platform engineering framework for building, modernizing, and operating secure Microsoft Azure environments.

This Architecture Charter defines the fundamental architectural principles, boundaries, responsibilities, and operating models of the project.

It is intended to act as the architectural baseline against which future implementation decisions, modules, features, extensions, and contributions are evaluated.

The charter deliberately separates architectural intent from implementation details.

Technology choices may evolve over time.

The architectural principles defined here should remain stable unless they are explicitly changed through an Architecture Decision Record.

---

# 2. Vision

Azure Platform Foundation aims to provide a reusable platform model that allows organizations to establish secure, governed, and maintainable Azure environments without requiring every consumer to understand the full complexity of Azure platform engineering.

The Foundation combines:

- Infrastructure as Code
- Identity and access management
- Governance and policy
- Security controls
- Connectivity
- Shared platform services
- Workload landing zones
- Controlled execution pipelines
- AI-assisted platform engineering

The central vision is:

> **Humans express intent.**  
> **AI translates intent.**  
> **Infrastructure as Code defines the desired state.**  
> **Policy defines the boundaries.**  
> **Pipelines establish reality.**

Artificial intelligence is therefore not a replacement for Infrastructure as Code, governance, or security controls.

AI is an additional interaction and orchestration layer that helps consumers and engineers work with the platform more efficiently.

---

# 3. Architectural Scope

Azure Platform Foundation provides the technical and organizational foundation required to operate Azure workloads in a controlled and repeatable manner.

The project supports both:

- **Greenfield environments**
- **Brownfield environments**

The Foundation is responsible for establishing or adopting the platform capabilities that surround application workloads.

These capabilities include:

- bootstrap and platform initialization;
- deployment identities;
- remote Terraform state;
- management group hierarchy;
- subscription organization;
- identity and access management;
- privileged access;
- Azure Policy;
- security baselines;
- centralized logging and monitoring;
- connectivity;
- DNS;
- shared platform services;
- workload landing zones;
- CI/CD integration;
- controlled deployment execution;
- platform configuration;
- customer-specific extensions;
- Brownfield discovery and assessment;
- AI-assisted platform engineering.

The Foundation does not primarily implement customer applications.

Its responsibility ends at the platform boundary on which application workloads are deployed.

The architectural boundary is therefore:

```text
Azure Platform Foundation
        │
        ├── Governance
        ├── Identity
        ├── Connectivity
        ├── Shared Platform Services
        └── Workload Landing Zones
                    │
                    ▼
              Application Workloads
```

Application teams may consume platform capabilities provided by the Foundation without becoming responsible for the implementation of the Foundation itself.

---

# 4. Product and Customer Separation

Azure Platform Foundation is designed as a reusable product.

The reusable Foundation implementation and customer-specific Azure environments must remain separated.

The product repository contains:

- reusable modules;
- configuration schemas;
- platform abstractions;
- governance definitions;
- policy catalogs;
- execution provider integrations;
- documentation;
- tooling;
- AI agent definitions;
- example configurations.

Customer-specific repositories contain:

- customer metadata;
- Azure tenant and subscription references;
- platform configuration;
- architecture decisions;
- enabled capabilities;
- customer-specific policies;
- customer-specific role mappings;
- approved exceptions;
- environment-specific parameters;
- references to versioned Foundation components.

The intended lifecycle is:

```text
Azure Platform Foundation
          │
          ▼
Customer Configuration
          │
          ▼
Customer Implementation Repository
          │
          ▼
Bootstrap
          │
          ▼
Level 0
          │
          ▼
Managed Azure Platform
```

Customer implementations should not require permanent forks of the Foundation.

Differences between customers should primarily be expressed through configuration, profiles, extensions, and explicit overrides.

---

# 5. Level Model

Azure Platform Foundation uses a layered model consisting of five levels.

A level describes an architectural responsibility.

It does not describe a specific Terraform module, repository, tool, or technology.

The level model is intentionally independent of implementation technology.

---

## 5.1 Level 0 – Bootstrap and Platform Control Plane

Level 0 establishes the minimum trusted environment required for the Azure Platform Foundation to manage itself.

The objective of Level 0 is:

> After Level 0 has been successfully established, normal platform operations no longer require a highly privileged local administrator or permanently stored Azure credentials.

Typical Level 0 capabilities include:

- bootstrap identity;
- Terraform remote state;
- state protection;
- deployment identities;
- workload identity federation;
- OIDC integration;
- CI/CD configuration;
- execution infrastructure;
- repository integration;
- platform metadata;
- deployment auditability;
- bootstrap handover.

The initial bootstrap process may require elevated permissions.

Those permissions must be considered temporary.

After handover, operational deployments must use dedicated platform identities with explicitly scoped permissions.

Level 0 therefore establishes the Foundation's **platform control plane**.

---

## 5.2 Level 1 – Governance, Identity and Security

Level 1 establishes the primary organizational and security boundaries of the Azure platform.

Typical capabilities include:

- management group hierarchy;
- subscription organization;
- identity model;
- RBAC model;
- privileged access;
- Azure Policy;
- policy initiatives;
- security baselines;
- Defender configuration;
- centralized logging;
- monitoring;
- compliance controls;
- governance metadata.

Level 1 answers the fundamental question:

> Who may perform which action, on which resource, under which conditions?

Permission design and governance are therefore first-class architecture components.

They must not be treated as secondary implementation details.

---

## 5.3 Level 2 – Connectivity and Shared Infrastructure

Level 2 provides shared network and connectivity capabilities.

Typical capabilities may include:

- hub-and-spoke networking;
- Azure Virtual WAN;
- virtual networks;
- subnet structures;
- routing;
- Azure Firewall;
- DNS;
- Private DNS;
- private connectivity;
- VPN connectivity;
- ExpressRoute integration;
- Bastion or management access;
- shared network services.

The Foundation provides reusable network patterns.

It must not assume that every customer uses the same topology.

Connectivity must therefore be modeled through explicit profiles and configuration.

---

## 5.4 Level 3 – Platform Services

Level 3 provides reusable services consumed by workloads and platform teams.

Possible platform services include:

- container registries;
- shared Key Vault services;
- monitoring services;
- automation services;
- DevOps infrastructure;
- private endpoint services;
- shared Kubernetes platforms;
- FinOps services;
- shared security services;
- AI platform services.

Platform services follow a capability model.

A service can typically be:

```text
enabled
disabled
existing
external
```

This allows Greenfield implementations to deploy platform services while Brownfield implementations can adopt or reference existing services.

---

## 5.5 Level 4 – Workload Landing Zones

Level 4 provides governed environments for application workloads.

A workload landing zone may include:

- subscription;
- resource organization;
- identity groups;
- RBAC;
- policies;
- networking;
- logging;
- monitoring;
- security baseline;
- budgets;
- lifecycle metadata;
- ownership metadata.

Different landing zone profiles may exist for different workload requirements.

Examples include:

```text
standard
developer
internet-facing
regulated
data
AI-workload
sandbox
```

The Foundation defines the platform boundary.

Application teams operate inside that boundary.

---

# 6. Greenfield Operating Model

A Greenfield deployment starts with a new or minimally configured Azure environment.

In Greenfield mode, the Foundation has a high level of authority over the desired platform state.

A typical sequence is:

```text
Bootstrap
    ↓
Level 0
    ↓
Level 1
    ↓
Level 2
    ↓
Level 3
    ↓
Level 4
```

The Foundation provides secure and opinionated defaults.

Customer-specific changes are expressed through configuration rather than through uncontrolled modifications of the core implementation.

A Greenfield deployment should be capable of establishing a complete platform foundation starting from:

```text
Microsoft Entra tenant
+
Azure subscription
+
Source control platform
+
Authorized bootstrap identity
```

Additional subscriptions and platform capabilities may be created or integrated during subsequent levels.

---

# 7. Brownfield Operating Model

Brownfield environments must not be treated like empty environments.

The primary Brownfield principle is:

> **Existing environments are discovered before they are changed.**

Brownfield therefore starts with discovery and assessment rather than deployment.

The intended process is:

```text
Existing Azure Environment
           ↓
        Discovery
           ↓
       Assessment
           ↓
 Gap and Conflict Analysis
           ↓
    Adoption Proposal
           ↓
        Approval
           ↓
 Incremental Adoption
```

Existing resources and configurations may be classified as:

```text
COMPLIANT
ACCEPTABLE
ADOPT
MIGRATE
REMEDIATE
EXCEPTION
UNMANAGED
```

The Foundation must avoid unnecessary replacement of existing infrastructure.

A Brownfield adoption should prefer:

- adoption;
- normalization;
- controlled remediation;
- explicit exceptions;
- incremental migration.

Destructive replacement is considered a deliberate migration decision and must not be the default behavior.

---

# 8. Permission Model

The Permission Model is a first-class architectural object.

Azure role assignments must not become an unstructured collection of implementation-specific resources.

The Foundation distinguishes between four identity categories:

```text
Human Identities
Platform Identities
Workload Identities
Agent Identities
```

---

## 8.1 Human Identities

Human access should primarily be granted through groups.

Direct role assignments to individual users should be avoided where practical.

Example functional roles include:

- Platform Owner;
- Platform Engineer;
- Security Operations;
- Network Operations;
- Workload Owner;
- Workload Developer;
- Auditor;
- FinOps.

Privileged permissions should be activated temporarily where possible.

Permanent highly privileged access should be minimized.

---

## 8.2 Platform Identities

Deployment and automation processes use dedicated platform identities.

Examples include:

```text
foundation-plan
foundation-apply
policy-remediation
subscription-vending
network-deployment
```

Responsibilities should be separated.

A single highly privileged deployment identity for every platform operation should be avoided.

Authentication should use:

- workload identity federation;
- OIDC;
- managed identities;
- short-lived credentials.

Long-lived client secrets should not be part of the default architecture.

---

## 8.3 Workload Identities

Applications and platform services should use dedicated workload identities.

Managed identities should be preferred where supported.

Control-plane and data-plane access should be considered separately.

A workload should receive only the permissions required for its intended function.

---

## 8.4 Agent Identities

AI agents are treated as platform identities.

They receive explicit roles, permissions, and restrictions.

An AI agent does not receive additional permissions because it is intelligent or autonomous.

Its privileges are derived exclusively from its assigned platform role.

A conceptual permission profile may look like:

```yaml
agent:
  name: platform-engineer

  allowed:
    - inventory.read
    - policy.read
    - architecture.read
    - terraform.validate
    - terraform.plan
    - repository.read
    - branch.create
    - pull-request.create
    - pipeline.validation.trigger

  conditional:
    - development.deploy

  prohibited:
    - production.direct-apply
    - privileged-role.assign
    - policy.disable
    - security-control.disable
```

Agent privileges must be enforced by deterministic authorization systems.

The language model itself is never considered a security boundary.

---

# 9. Policy and Governance Model

Azure Policy and governance form a core security boundary of the platform.

The Foundation uses a policy catalog rather than an unstructured collection of policy assignments.

The catalog may contain:

```text
Core Baseline
    │
    ├── Security
    ├── Identity
    ├── Networking
    ├── Monitoring
    ├── Data Protection
    ├── Resource Standards
    └── Cost Governance

Extended Baselines
    │
    ├── Enterprise
    ├── Regulated
    ├── Developer
    ├── Internet-facing
    └── AI Workloads

Customer Extensions
```

Each policy should include metadata describing:

- category;
- purpose;
- severity;
- enforcement mode;
- Greenfield behavior;
- Brownfield behavior;
- remediation support;
- exception handling;
- ownership.

Example:

```yaml
policy:
  name: deny-public-ip

  category: networking
  severity: high

  greenfield:
    enforcement: deny

  brownfield:
    enforcement: audit

  remediation:
    supported: true

  exception:
    allowed: true
    approval: security
```

Brownfield policies may follow an incremental lifecycle:

```text
Audit
  ↓
Assessment
  ↓
Remediation
  ↓
Controlled Enforcement
  ↓
Deny
```

Governance must not depend on users or AI agents always making correct decisions.

Guardrails must therefore be enforced through deterministic platform controls.

---

# 10. Execution Plane

The Execution Plane is responsible for applying platform changes.

It is intentionally separated from both human interaction and AI reasoning.

The execution flow is:

```text
Human or AI Agent
       │
       ▼
Platform Request
       │
       ▼
Infrastructure-as-Code Change
       │
       ▼
Pull Request
       │
       ▼
Validation
       │
       ├── Formatting
       ├── Static Validation
       ├── Terraform Plan
       ├── Security Checks
       ├── Policy Checks
       ├── Architecture Checks
       └── Optional Cost Analysis
       │
       ▼
Approval
       │
       ▼
Trusted Execution Plane
       │
       ▼
Azure
```

The Execution Plane follows these principles:

- Infrastructure changes are version controlled.
- Pull requests are the default change mechanism.
- Authentication uses short-lived identities.
- Long-lived deployment credentials are avoided.
- Execution is auditable.
- Production changes require explicit control.
- Pipelines remain deterministic.
- AI agents do not bypass pipeline controls.

The initial execution providers are:

```text
GitHub Actions
Azure DevOps Pipelines
```

The Foundation architecture must remain independent of a specific CI/CD provider.

Provider-specific integrations are adapters to the Execution Plane.

---

# 11. AI Platform Engineering Model

AI is a horizontal capability of the Azure Platform Foundation.

It is not implemented as an additional Foundation level.

The AI Platform Engineering layer interacts with all Foundation levels.

Conceptually:

```text
                 AI Platform Engineer
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
     Level 0          Level 1          Level 2 ...
```

The initial AI role is:

## AI Platform Engineer

The AI Platform Engineer supports six primary capabilities.

### DISCOVER

Understand Azure environments and Foundation configuration.

### EXPLAIN

Explain architecture, policies, permissions, deployments, and platform decisions.

### DESIGN

Translate user requirements into Foundation configuration and platform requests.

### PLAN

Prepare infrastructure changes and analyze their expected impact.

### IMPLEMENT

Prepare code, configuration, branches, and pull requests.

### OPERATE

Analyze deployment results, failures, drift, and operational conditions.

The AI Platform Engineer does not receive unrestricted access to Azure.

It interacts with the platform through explicitly defined tools.

Examples include:

```text
azure.inventory.read()

foundation.architecture.read()

foundation.policy_catalog.read()

foundation.permission_model.read()

landingzone.profile.list()

platform.request.validate()

terraform.validate()

terraform.plan()

repository.branch.create()

repository.pull_request.create()

pipeline.validation.trigger()

pipeline.result.read()
```

Unrestricted command interfaces should not be the default mechanism for agent interaction.

For example, the Foundation should avoid granting agents generic capabilities equivalent to:

```text
run arbitrary Azure CLI command
```

or:

```text
run arbitrary Terraform apply
```

where a narrower capability can be provided instead.

---

# 12. AI Autonomy Model

Azure Platform Foundation defines explicit AI autonomy levels.

## A0 – Advisor

The agent may:

- read;
- analyze;
- explain;
- recommend.

The agent may not modify platform state.

---

## A1 – Contributor

The agent may additionally:

- create configuration;
- prepare Infrastructure-as-Code changes;
- create branches;
- create pull requests;
- trigger validation workflows.

The agent may not directly modify production infrastructure.

This is the initial target autonomy level for Azure Platform Foundation.

---

## A2 – Operator

The agent may perform explicitly approved operations in controlled non-production environments.

Examples may include:

- approved DEV deployments;
- safe remediation;
- controlled operational actions.

---

## A3 – Autonomous Operator

The agent may execute predefined actions without individual human approval.

This level is only appropriate where deterministic guardrails, bounded permissions, auditability, and rollback mechanisms exist.

A3 is not considered the default operating model.

---

# 13. Configuration over Custom Code

Customer-specific differences should primarily be expressed through configuration.

The Foundation should not require customers to edit large amounts of reusable implementation code.

Example:

```yaml
customer:
  id: contoso

azure:
  primary_region: germanywestcentral

deployment:
  mode: greenfield

execution:
  provider: github

network:
  topology: hub_spoke

governance:
  profile: enterprise
```

The Foundation translates this higher-level model into the required Azure and Infrastructure-as-Code configuration.

The architectural goal is:

> Consumers describe what they need.  
> The Foundation determines how that requirement is implemented according to platform standards.

Implementation details should remain accessible to experienced platform engineers.

Abstraction must not prevent expert control.

---

# 14. Technology Abstraction

Azure Platform Foundation may use technologies such as:

- Terraform;
- Azure Verified Modules;
- Microsoft Entra ID;
- Azure Policy;
- GitHub Actions;
- Azure DevOps;
- managed identities;
- workload identity federation;
- Microsoft Foundry;
- Model Context Protocol.

However, the architecture must not unnecessarily expose implementation-specific concepts to platform consumers.

For example:

```text
Customer Configuration
        ↓
APF Platform Model
        ↓
APF Implementation
        ↓
Azure Verified Modules
        ↓
Azure
```

Customers should primarily interact with the APF platform model.

Underlying implementation technologies remain replaceable where practical.

---

# 15. Architecture Principles

The following principles are considered mandatory unless an explicit Architecture Decision Record defines an exception.

## Principle 1 – Everything Important Is Declarative

Relevant platform state must be described through version-controlled code or structured configuration.

Manual changes must not become the authoritative platform definition.

---

## Principle 2 – Existing Environments Are Discovered Before They Are Changed

Brownfield environments require discovery and assessment before remediation or adoption.

The Foundation must not assume ownership of resources it does not understand.

---

## Principle 3 – Identity Is a Security Boundary

Humans, pipelines, workloads, automation processes, and AI agents use separate identities.

Permissions follow least-privilege principles.

---

## Principle 4 – Policy Defines the Guardrails

Security and compliance controls must be enforced through deterministic platform mechanisms.

Correct behavior must not depend exclusively on human or AI judgment.

---

## Principle 5 – AI Proposes; Deterministic Systems Execute

AI may interpret, plan, generate, explain, and orchestrate.

Critical infrastructure changes are validated and applied through deterministic Infrastructure-as-Code and pipeline mechanisms.

---

## Principle 6 – The Foundation Is CI/CD Independent

GitHub Actions and Azure DevOps are execution providers.

Neither provider defines the Foundation architecture.

Provider-specific logic must remain separated from the platform model.

---

## Principle 7 – Complexity Belongs in the Platform

Platform consumers should not need to understand every technical implementation detail.

Complexity should be encapsulated behind:

- configuration;
- profiles;
- catalogs;
- platform requests;
- documentation;
- AI-assisted interfaces.

---

## Principle 8 – Secure Defaults over Optional Security

Security controls should be enabled by default.

Disabling a control should require an explicit decision or documented exception.

---

## Principle 9 – Customer-Specific Data Does Not Belong in the Product Repository

The public Foundation repository must remain reusable and free from customer-specific confidential information.

Customer configuration belongs in customer implementation repositories.

---

## Principle 10 – Bootstrap Privilege Is Temporary

Elevated permissions used during initial platform creation must not become the permanent operational model.

The Foundation must transition from bootstrap access to dedicated platform identities.

---

## Principle 11 – Changes Must Be Auditable

Platform changes must be attributable to:

- an identity;
- a change request;
- a source revision;
- an execution;
- an outcome.

This applies equally to human and AI-originated changes.

---

## Principle 12 – Architecture Before Automation

Automation does not justify an unclear architecture.

New automation, modules, agents, and pipelines must align with the Architecture Charter before they are implemented.

---

# 16. Initial Implementation Milestone

The first implementation milestone is:

## M0 – Greenfield Bootstrap

Starting requirements:

```text
Microsoft Entra tenant
+
One Azure subscription
+
GitHub or Azure DevOps
+
One authorized bootstrap identity
```

The expected result is:

```text
Customer configuration
+
Customer implementation repository
+
Terraform remote state
+
Platform deployment identities
+
Workload identity federation / OIDC
+
CI/CD integration
+
Operational Level 0
```

After M0, the following workflow must be possible:

```text
Git Change
    ↓
Pull Request
    ↓
Validation
    ↓
Terraform Plan
    ↓
Approval
    ↓
Apply
    ↓
Azure
```

without requiring permanently stored Azure deployment credentials.

---

# 17. Level 0 Definition of Done

Level 0 is considered successfully implemented when:

- a new customer implementation can be initialized from the generic Foundation;
- customer-specific configuration is separated from the Foundation repository;
- Terraform state is stored remotely and protected;
- deployment identities are created;
- authentication uses workload identity federation or equivalent short-lived mechanisms;
- no permanent Azure client secret is required for normal deployments;
- GitHub Actions are supported;
- Azure DevOps Pipelines are supported;
- deployments are reproducible;
- repeated deployment is idempotent;
- the Foundation version can be explicitly pinned;
- bootstrap privileges are no longer required for normal operations;
- platform changes can be executed through source control and pipeline workflows;
- execution is auditable.

---

# 18. Architecture Decision Records

Significant architectural decisions must be documented through Architecture Decision Records under:

```text
docs/adr/
```

An ADR should be created when a decision:

- introduces a major technology;
- changes an architectural boundary;
- changes the permission model;
- changes the execution model;
- changes the configuration model;
- introduces a new supported platform provider;
- changes an Architecture Principle;
- creates a long-term compatibility obligation.

The Architecture Charter defines the overall framework.

ADRs document individual decisions inside that framework.

---

# 19. Change Management

Changes to this Architecture Charter should be intentional and reviewed.

A proposed change should answer:

1. What architectural problem is being solved?
2. Which existing principle is insufficient?
3. What compatibility impact does the change introduce?
4. Does the change affect Greenfield, Brownfield, or both?
5. Does the change affect the security model?
6. Does the change affect customer implementations?
7. Does the change require an ADR?

Minor editorial improvements do not require a new Architecture Charter version.

Architectural changes should update the version and associated ADRs.

---

# 20. Closing Principle

Azure Platform Foundation is not intended to become a collection of deployment scripts.

It is intended to become a reusable platform product.

Its purpose is to provide a secure and understandable boundary between:

```text
Business and Engineering Intent
            ↓
Platform Configuration
            ↓
Governance and Architecture
            ↓
Infrastructure as Code
            ↓
Controlled Execution
            ↓
Microsoft Azure
```

AI improves how users interact with this platform.

It does not replace the platform itself.

The final design principle is therefore:

> **We are not replacing Infrastructure as Code with AI.**  
> **We are making Infrastructure as Code accessible through AI.**