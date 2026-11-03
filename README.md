# Azure Platform Foundation

**Secure by design. AI-assisted. Ready for Greenfield and Brownfield.**

> **Project status:** Early development / architecture phase  
> The project is currently being designed and implemented. Interfaces, structures, and deployment models may change until the first stable release.

## Overview

**Azure Platform Foundation (APF)** is an Infrastructure-as-Code-based platform engineering framework for building, modernizing, and operating secure Microsoft Azure environments.

The project is designed to provide a reusable and opinionated foundation for organizations that want to establish Azure environments according to modern cloud, security, governance, and automation principles without forcing every consumer to understand the full complexity behind the platform.

Azure Platform Foundation supports both **Greenfield** and **Brownfield** scenarios.

In a Greenfield scenario, APF can initialize a new Azure platform from the ground up, including bootstrap capabilities, identity and permission models, governance, policies, connectivity, shared platform services, and workload landing zones.

In a Brownfield scenario, APF is intended to discover and assess an existing Azure environment first, identify gaps and conflicts, and support the controlled adoption of platform standards without blindly replacing existing infrastructure.

A dedicated **AI Platform Engineering layer** will make the platform easier to consume by translating user intent into controlled, auditable Infrastructure-as-Code changes.

The core principle is simple:

> **Humans express intent.**  
> **AI translates intent.**  
> **Infrastructure as Code defines the desired state.**  
> **Policy defines the boundaries.**  
> **Pipelines establish reality.**

---

## Why Azure Platform Foundation?

Building an Azure platform is not primarily a resource deployment problem.

A sustainable enterprise platform requires consistent decisions across areas such as identity, permissions, governance, policy, networking, security, monitoring, deployment automation, and workload isolation.

These decisions are often distributed across multiple repositories, teams, scripts, documents, and deployment pipelines.

Azure Platform Foundation aims to provide a coherent platform model that combines these concerns into a reusable foundation while keeping customer-specific configuration separate from the underlying product implementation.

The project is designed around several goals:

- provide a secure and reproducible Azure foundation;
- support both new and existing Azure environments;
- establish a strong permission and governance model from the beginning;
- use Infrastructure as Code as the authoritative platform definition;
- avoid long-lived deployment credentials wherever possible;
- support GitHub and Azure DevOps as execution providers;
- make platform capabilities consumable through standardized configuration;
- reduce platform complexity through AI-assisted workflows;
- keep AI agents inside clearly defined security and governance boundaries;
- allow customer environments to evolve independently from the core framework.

---

# Architecture Model

Azure Platform Foundation follows a layered architecture.

```text
                    ┌─────────────────────────┐
                    │      Consumers          │
                    │                         │
                    │ Teams / Engineers / AI  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ AI Platform Engineering │
                    │                         │
                    │ Discover • Explain      │
                    │ Design • Plan • Operate │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Platform Contract     │
                    │                         │
                    │ Config / Requests       │
                    │ Profiles / Policies     │
                    └────────────┬────────────┘
                                 │
                                 ▼
              ┌────────────────────────────────────┐
              │      Azure Platform Foundation     │
              │                                    │
              │ L0  Bootstrap & Control Plane      │
              │ L1  Governance, Identity, Security │
              │ L2  Connectivity                   │
              │ L3  Platform Services              │
              │ L4  Workload Landing Zones         │
              └─────────────────┬──────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    Execution Plane      │
                    │                         │
                    │ Validate • Plan         │
                    │ Approve • Apply         │
                    └────────────┬────────────┘
                                 │
                                 ▼
                               Azure
```

---

# Foundation Levels

## Level 0 – Bootstrap & Control Plane

Level 0 establishes the minimum trusted environment required for the platform to manage itself.

Typical capabilities include:

```text
Terraform remote state
Deployment identities
Workload identity federation / OIDC
CI/CD integration
Execution infrastructure
Repository integration
Foundation metadata
Auditability
Bootstrap handover
```

After Level 0 has been completed, normal platform deployments should no longer depend on a highly privileged local administrator or long-lived Azure credentials.

---

## Level 1 – Governance, Identity & Security

Level 1 establishes the primary security and governance boundaries of the Azure platform.

Typical capabilities include:

```text
Management group hierarchy
Subscription organization
RBAC model
Privileged access model
Azure Policy
Security baseline
Defender configuration
Central logging
Monitoring
Compliance controls
```

Permission design and policy governance are first-class architecture components of the Foundation.

---

## Level 2 – Connectivity & Shared Infrastructure

Level 2 provides common connectivity and network services.

Depending on customer requirements, this can include:

```text
Hub-and-Spoke networking
Azure Virtual WAN
DNS and Private DNS
Azure Firewall
Routing
VPN / ExpressRoute integration
Private connectivity
Management access
Shared network services
```

The Foundation defines reusable network patterns without requiring every customer to use exactly the same topology.

---

## Level 3 – Platform Services

Level 3 provides reusable shared services consumed by workloads and platform teams.

Examples may include:

```text
Container registries
Shared Key Vault services
Monitoring services
Automation services
DevOps infrastructure
Private endpoint services
Shared Kubernetes platforms
FinOps services
AI platform services
```

Platform services are capability-driven and can be enabled, disabled, externally provided, or mapped to existing customer services.

---

## Level 4 – Workload Landing Zones

Level 4 provides governed environments in which application workloads can operate.

A workload landing zone can include:

```text
Subscription
Identity groups
RBAC
Policies
Networking
Logging
Security baseline
Budget controls
Lifecycle metadata
```

Different landing zone profiles can be provided for different workload requirements, for example:

```text
standard
developer
internet-facing
regulated
data
AI workload
sandbox
```

---

# Greenfield

In Greenfield mode, Azure Platform Foundation establishes a new Azure platform based on a defined target architecture.

A typical deployment flow is:

```text
Bootstrap
    ↓
Level 0
    ↓
Governance & Identity
    ↓
Policy & Security
    ↓
Connectivity
    ↓
Platform Services
    ↓
Workload Landing Zones
```

The goal is to provide secure defaults while still allowing organizations to adapt the Foundation to their requirements.

---

# Brownfield

Brownfield adoption follows a different principle:

> **Existing environments are understood before they are changed.**

A Brownfield workflow is therefore expected to start with discovery and assessment.

```text
Existing Azure Environment
           ↓
        Discovery
           ↓
       Assessment
           ↓
 Gap / Conflict Analysis
           ↓
    Adoption Proposal
           ↓
        Approval
           ↓
 Incremental Adoption
```

Existing resources and configurations can be classified, for example, as:

```text
COMPLIANT
ACCEPTABLE
ADOPT
MIGRATE
REMEDIATE
EXCEPTION
UNMANAGED
```

The objective is not to rebuild an existing Azure estate unnecessarily, but to move it incrementally toward a controlled and documented platform model.

---

# Customer Project Model

Azure Platform Foundation separates the reusable framework from customer-specific implementations.

The core repository represents the product:

```text
azure-platform-foundation
```

Customer environments are expected to use separate implementation repositories:

```text
contoso-azure-platform
fabrikam-azure-platform
customer-x-azure-platform
```

The intended lifecycle is:

```text
Azure Platform Foundation
          │
          ▼
Customer Configuration
          │
          ▼
Customer Repository
          │
          ▼
Bootstrap
          │
          ▼
Level 0
          │
          ▼
Self-managed Azure Platform
```

Customer repositories should primarily contain configuration, architecture decisions, extensions, exceptions, and references to versioned Foundation components.

Customer-specific data must not become part of the public Foundation repository.

---

# Configuration over Custom Code

A key design objective is to avoid customer-specific forks of the Foundation.

Differences between environments should primarily be expressed through configuration and profiles.

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

The Foundation translates this higher-level platform configuration into the required Azure and Infrastructure-as-Code implementation.

Consumers should not need to understand every underlying Terraform or Azure Verified Module parameter.

---

# Execution Plane

AI agents and human users do not directly replace the deployment pipeline.

Infrastructure changes are executed through a deterministic and auditable execution plane.

```text
Human / AI Agent
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
       ├── Validation
       ├── Terraform Plan
       ├── Security Checks
       ├── Policy Checks
       └── Architecture Rules
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

The initial execution providers are planned to be:

```text
GitHub Actions
Azure DevOps Pipelines
```

The Foundation itself should remain independent of either provider.

Authentication should use workload identity federation, OIDC, managed identities, and short-lived credentials wherever possible.

---

# AI Platform Engineering

Artificial intelligence is a platform capability, not a replacement for Infrastructure as Code, policy, or security controls.

The initial AI role is the:

## AI Platform Engineer

The AI Platform Engineer is intended to support six primary capabilities:

```text
DISCOVER
Understand existing Azure environments.

EXPLAIN
Explain Foundation architecture and platform decisions.

DESIGN
Translate requirements into platform configuration.

PLAN
Prepare and assess infrastructure changes.

IMPLEMENT
Prepare Infrastructure-as-Code changes and pull requests.

OPERATE
Analyze deployments and assist with troubleshooting.
```

The AI Platform Engineer works through explicitly defined tools and permissions.

It should not receive unrestricted administrative access to Azure.

A typical first autonomy model is:

```text
A0  Advisor
    Read, analyze, explain.

A1  Contributor
    Create configuration, code, branches, and pull requests.

A2  Operator
    Execute explicitly approved actions in non-production environments.

A3  Autonomous Operator
    Perform predefined operations inside strict technical guardrails.
```

The initial target for Azure Platform Foundation is **A1 – Contributor**.

---

# Security Principles

Azure Platform Foundation follows several fundamental security principles:

```text
Least privilege by default

Separate identities for humans, pipelines,
workloads, and AI agents

No permanent administrative deployment accounts

No long-lived Azure deployment secrets where
workload identity federation is available

Infrastructure changes are version controlled

Production changes are auditable

Policies enforce platform boundaries

AI decisions never replace deterministic
security controls
```

The central rule is:

> **An AI agent receives permissions because of its assigned role, not because of its intelligence.**

---

# Technology Direction

Azure Platform Foundation is expected to use modern Azure and open infrastructure technologies, including:

```text
Microsoft Azure

Terraform

Azure Verified Modules

Microsoft Entra ID

Azure Policy

GitHub Actions

Azure DevOps

Workload Identity Federation / OIDC

Managed Identities

Microsoft Foundry

Model Context Protocol (MCP)
```

Individual implementation decisions will be documented through Architecture Decision Records (ADRs).

---

# Repository Structure

The planned repository structure is:

```text
azure-platform-foundation/
│
├── docs/
│   ├── architecture/
│   └── adr/
│
├── config/
│   └── schema/
│
├── foundation/
│   ├── levels/
│   │   ├── level0/
│   │   ├── level1/
│   │   ├── level2/
│   │   ├── level3/
│   │   └── level4/
│   │
│   └── modules/
│
├── governance/
│   ├── policies/
│   └── permissions/
│
├── execution/
│   ├── github/
│   └── azure-devops/
│
├── tooling/
│   ├── bootstrap/
│   └── customer-init/
│
└── README.md
```

The structure will evolve as the architecture is implemented.

---

# Initial Milestone

The first implementation milestone is:

## M0 – Greenfield Bootstrap

Starting point:

```text
Microsoft Entra tenant
+
One Azure subscription
+
GitHub or Azure DevOps
+
One authorized bootstrap identity
```

Expected result:

```text
Customer configuration
+
Customer repository
+
Terraform remote state
+
Deployment identities
+
OIDC / workload identity federation
+
CI/CD pipeline
+
Operational Level 0
```

After M0, a normal infrastructure change should be deployable through the platform pipeline without requiring locally stored Azure credentials.

---

# Current Project Phase

The project is currently focused on establishing:

```text
Architecture model

Customer project model

Configuration schema

Greenfield initialization

Level 0 bootstrap

GitHub execution provider

Azure DevOps execution provider
```

Level 1 through Level 4 and advanced AI capabilities will be implemented incrementally after the Level 0 lifecycle has been validated.

---

# Contributing

Azure Platform Foundation is currently in an early development stage.

Contribution guidelines, coding standards, testing requirements, and the extension model will be added as the first implementation becomes available.

---

# License

The project license will be defined before the first public release.

---

# Vision

Azure Platform Foundation aims to turn Azure platform engineering into a reusable and accessible product rather than a collection of individual deployment scripts.

Experienced Platform Engineers should retain full control over Infrastructure as Code and architecture decisions.

At the same time, consumers should increasingly be able to describe **what they need** instead of having to understand every technical implementation detail behind the platform.

> **We are not replacing Infrastructure as Code with AI.  
> We are making Infrastructure as Code accessible through AI.**
