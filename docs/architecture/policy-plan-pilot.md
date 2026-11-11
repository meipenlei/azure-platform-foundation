# Policy Desired-State Plan Pilot

**Version:** 0.1  
**Status:** Commit 11  
**Azure mutation:** None

## Purpose

Commit 11 proves the APF-to-EPAC desired-state path before any policy deployment
is permitted.

The pilot validates that APF can generate deterministic EPAC input, authenticate
secretlessly, compare desired state with Azure and expose the plan for review.

## Execution boundary

    Pull Request
        |
        v
    GitHub OIDC
        |
        v
    APF Plan UAMI
        |
        | Reader only
        v
    Build-DeploymentPlans
        |
        v
    EPAC plan artifact

The Governance UAMI is not used by this workflow.

There is no `Deploy-PolicyPlan` or `Deploy-RolesPlan` step.

## Why subscription scope first?

APF has completed Level 0 but has not yet created the Level 1 management-group
hierarchy.

The Microsoft ALZ/SLZ assignment model is management-group oriented. Activating
full ALZ synchronization before those scopes exist would couple the first EPAC
proof to infrastructure APF has not created yet.

Commit 11 therefore uses the bootstrap subscription as a temporary deployment
root.

## First desired state

The pilot contains one assignment derived from the legacy governance library:

    CAF-Deny-Public-IP

Its current Microsoft upstream assignment is:

    Deny-Public-IP

APF deliberately preserves the old audit-first behavior:

    effect = Audit
    enforcementMode = Default

The assignment is observable but non-blocking.

## Desired-state ownership

The pilot uses:

    desiredState.strategy = ownedOnly

Commit 11 is proving the policy engine, not claiming complete policy ownership
of the subscription.

## Stable EPAC ownership ID

Each generated customer repository receives a deterministic UUIDv5
`pacOwnerId`, derived from the immutable GitHub owner ID and repository ID.

This provides a stable ownership marker without adding a secret or manually
maintained identifier.

## Next stage

After Commit 11 is proven:

1. introduce the Level 1 management-group hierarchy;
2. move the policy deployment root to the intended management group;
3. generate ALZ/SLZ structures from the pinned library versions;
4. preserve APF audit/Brownfield overrides from the migration inventory;
5. review the EPAC plan;
6. only then add a separately protected Policy Apply workflow.
