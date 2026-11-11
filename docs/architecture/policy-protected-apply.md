# Protected Policy Apply

**Status:** Commit 15  
**Execution:** Manual protected apply  
**Desired state:** `ownedOnly`  
**Policy content:** unchanged from Audit-First Wave 1

## Purpose

Commit 15 introduces the first APF Azure Policy mutation path only after the
plan-only lifecycle has been proven at subscription and management-group
scope.

The commit intentionally changes execution capability, not policy scope or
policy content.

## Identity boundary

Pull-request planning remains separate from deployment:

    Pull Request
        |
        v
    Plan UAMI
        |
        v
    Build-DeploymentPlans

The protected apply path is:

    workflow_dispatch on main
        |
        v
    GitHub environment: apf-governance
        |
        v
    Governance UAMI
        |
        v
    Build-DeploymentPlans
        |
        v
    APF additive-only plan guard
        |
        v
    Deploy-PolicyPlan
        |
        v
    Deploy-RolesPlan
        |
        v
    Build-DeploymentPlans again
        |
        v
    zero-change convergence check

The Governance UAMI uses the existing environment-scoped OIDC federation. No
client secret, PAT or storage key is introduced.

## Why rebuild the plan at apply time?

The pull-request plan proves the proposed source change, but Azure can change
between PR review and deployment. Commit 15 therefore rebuilds the plan on the
trusted `main` branch immediately before mutation.

The apply workflow does not blindly deploy an old PR artifact.

## Apply guard

The generated guard is stored in the customer repository at:

    governance/policy/tooling/verify_apply_plan.py

For Commit 15 it permits only new Policy Assignments whose resource IDs can be
derived from the checked-in assignment Definitions for the selected PAC
environment.

It rejects all of the following before any deployment command runs:

- unknown assignment IDs;
- assignment updates;
- assignment replacements;
- assignment deletes;
- Policy Definition changes;
- Policy Set Definition changes;
- exemption changes;
- enrollment changes;
- role-assignment changes;
- a plan with a mismatched `pacOwnerId`.

A missing plan file is treated as a safe no-op, which makes repeated apply
runs idempotent.

## Deployment order

EPAC policy resources are deployed before role assignments:

    Deploy-PolicyPlan
    Deploy-RolesPlan

That order is compatible with future identity-bearing assignments because
role plans can depend on the identity created by a Policy Assignment.

Commit 15 nevertheless blocks role changes entirely. Role reconciliation is a
later capability increment.

## Post-apply verification

After deployment, APF runs `Build-DeploymentPlans` again against Azure. The
post-apply guard requires zero policy changes and zero role changes.

A non-zero post-apply plan fails the workflow even if the deployment command
itself succeeded. This makes convergence part of the apply contract.
