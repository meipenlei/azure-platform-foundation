# Level 1 Management Group Foundation

**Status:** Commit 12  
**Owner:** Terraform / APF  
**Policy deployment:** Not part of Commit 12

## Design

Commit 12 establishes the Azure resource hierarchy that the later ALZ/SLZ
policy model requires.

    Tenant Root
      |
      +-- APF Root
          |
          +-- Platform
          |   +-- Management
          |   +-- Connectivity
          |   +-- Identity
          |
          +-- Landing Zones
          |   +-- Corp
          |   +-- Online
          |
          +-- Sandboxes
          +-- Decommissioned

The APF root management-group ID is the customer naming prefix. Child IDs are
derived deterministically from that prefix.

## Bootstrap boundary

The first apply is deliberately special.

A locally signed-in privileged operator creates the APF Root and delegates
ongoing management at that scope. APF does not place a permanent role
assignment on the Tenant Root management group.

After bootstrap:

- the Plan UAMI can read the APF hierarchy;
- the Governance UAMI can manage the hierarchy;
- the Governance UAMI can assign Azure Policy within the hierarchy;
- the Governance UAMI can manage RBAC required by governance operations.

This keeps the durable APF security boundary below the Tenant Root.

## Subscription placement

The existing Level 0 bootstrap subscription is associated with the
`Management` management group.

Subscription placement uses
`azurerm_management_group_subscription_association`.

APF does not also populate `subscription_ids` on management group resources.

## Terraform state

Management-group state is independent:

    level1.management-groups.tfstate

The state uses the Level 0 Azure Storage backend.

## CI/CD handover

After the bootstrap apply:

    Pull Request
        |
        v
    Plan UAMI / Reader
        |
        v
    Terraform Plan

and:

    apf-governance environment
        |
        v
    Governance UAMI
        |
        +-- Management Group Contributor
        +-- Resource Policy Contributor
        +-- Role Based Access Control Administrator
        |
        v
    Terraform Apply

## Policy handover

Commit 11 intentionally remains scoped to the bootstrap subscription.

Commit 12 exposes the APF root ID as:

    policy_deployment_root_scope

The next policy commit will consume this value to move EPAC planning from the
temporary subscription scope to the APF Root management group.
