# Level 1 Management & Security Substrate

**Status:** Commit 18  
**Terraform owner:** APF  
**Policy owner:** EPAC  
**Azure mutation in this commit:** Management platform resources only

## Purpose

Level 1 must establish central observability anchors before Level 2
connectivity and shared infrastructure are deployed.

Commit 18 creates the stable resources that later Policy-as-Code assignments
reference. It deliberately does not yet create policy assignments, DCR
associations, Defender plans, diagnostic settings, remediation tasks, or
workload resources.

## Subscription model

APF accepts an optional:

    customer.azure.management_subscription_id

When supplied, central management resources are deployed to that subscription.
When omitted, APF falls back to the existing Level 0 bootstrap subscription.
This keeps labs simple without baking that simplification into the product
architecture.

Both the bootstrap subscription and an optional dedicated Management
subscription are placed below the APF `Management` management group.

## Identity boundary

The Plan UAMI retains Reader at APF Root.

The Governance UAMI receives `Contributor` only at the APF `Management`
management group. It can therefore create central management resources in
subscriptions placed below that management group without receiving Contributor
on workload Landing Zones.

The existing governance roles at APF Root remain unchanged:

- Management Group Contributor;
- Resource Policy Contributor;
- Role Based Access Control Administrator.

## Terraform-owned anchor resources

Commit 18 creates:

    <prefix>-rg-l1-management
    <prefix>-law-l1-platform
    <prefix>-id-l1-monitoring

The central Log Analytics workspace:

- uses `PerGB2018`;
- has configurable retention (30–730 days, default 30);
- allows resource-context access;
- disables local/shared-key authentication;
- keeps public ingestion/query enabled until the later connectivity/private-link
  architecture exists.

The monitoring UAMI is created now because later Azure Monitor/AMA policy
assignments need a stable identity resource ID. Commit 18 assigns no workload
permissions to that identity.

## Deliberately deferred

Commit 18 does not create:

- Data Collection Rules;
- Data Collection Endpoints;
- Azure Monitor Agent assignments;
- Activity Log diagnostic settings;
- resource diagnostic settings;
- Defender for Cloud plans;
- Defender continuous export;
- Microsoft Sentinel;
- Action Groups or alert rules;
- remediation tasks.

These depend on policy/runtime choices that are implemented in later commits.

## State separation

Management-group hierarchy/RBAC remains in:

    level1.management-groups.tfstate

Management platform resources use:

    level1.management-platform.tfstate

Both states use the existing secretless Level 0 backend.

## Policy integration contract

The customer generator writes:

    .foundation/level1-management-platform.yaml

It contains deterministic resource IDs for the Log Analytics workspace and
monitoring UAMI. Later EPAC generators consume these IDs rather than
reconstructing Azure names independently.

## Required deployment order

    Level 1 Management Groups / RBAC
        |
        v
    Level 1 Management Platform
        |
        v
    DINE / Modify execution model
        |
        v
    Defender + Monitoring policy baseline
        |
        v
    Level 1 readiness gate
        |
        v
    Level 2 Connectivity

Level 2 must not be treated as ready until the later Level 1 readiness gate
confirms governance, monitoring, security and remediation are operational.
