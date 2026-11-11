# APF Customer Policy Configurator

This tool generates the EPAC desired-state configuration in an existing APF
customer repository.

Commit 15 adds the first **protected Policy Apply** path without expanding the
Wave 1 policy content.

## Required Level 1 input

The configurator requires:

    .foundation/level1-management-groups.yaml

The EPAC deployment root remains the APF root management group, while each
policy assignment resolves its target management group from
`management_group_ids` in that snapshot.

There is no scope fallback and no inferred `security` mapping.

## Wave 1 assignments

| Upstream assignment | Legacy archetype | APF scope | Preserved behavior |
| --- | --- | --- | --- |
| `Deny-Public-IP` | `es_identity` | `identity` | `Default`, `effect=Audit` |
| `Deny-Classic-Resources` | `es_root` | `root` | `DoNotEnforce`, `effect=Deny` |
| `Deny-Storage-http` | `es_landing_zones` | `landing_zones` | `DoNotEnforce`, `effect=Deny` |
| `Deny-HybridNetworking` | `es_corp` | `corp` | `DoNotEnforce`, `effect=Deny` |

These assignments use built-in policy definitions and require no managed
identity or policy-assignment RBAC.

## CI/CD boundary

The generated plan workflow:

- runs on pull requests;
- authenticates with `AZURE_PLAN_CLIENT_ID`;
- uses OIDC;
- invokes `Build-DeploymentPlans` only;
- never invokes `Deploy-PolicyPlan` or `Deploy-RolesPlan`.

The generated apply workflow:

- is `workflow_dispatch` only;
- accepts execution only from `main`;
- uses the `apf-governance` GitHub environment;
- authenticates with `AZURE_GOVERNANCE_CLIENT_ID` via OIDC;
- rebuilds the EPAC plan immediately before deployment;
- verifies the plan with the generated APF apply guard;
- calls `Deploy-PolicyPlan` and then `Deploy-RolesPlan`;
- rebuilds the plan after deployment and requires zero remaining changes.

The apply guard allows only **new Policy Assignments that already exist in the
generated Definitions tree**. It rejects assignment updates/replaces/deletes,
Policy Definitions, Policy Set Definitions, exemptions, enrollments and all
role-assignment changes.

This boundary is intentionally narrower than EPAC's full capability. DINE,
Modify and assignment-role reconciliation remain deferred.

## Dry run

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

## Generate

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

The command is deterministic and idempotent.

## Generated apply tooling

The configurator copies the versioned guard into the customer repository:

    governance/policy/tooling/verify_apply_plan.py

The customer workflow therefore does not download or execute mutable APF
runtime code during an apply.

## Deliberately deferred

Legacy assignments from the `security` archetype are not included in Wave 1.
APF does not yet have an explicit target scope for that horizontal archetype,
so the generator refuses to guess one.
