# Azure Platform Foundation Policy Layer

The APF Policy Layer implements Governance as Code for Azure Policy.

## Ownership boundary

APF deliberately separates infrastructure ownership from policy ownership.

| Capability | Declarative owner |
| --- | --- |
| Management groups | Terraform / APF |
| Platform managed identities | Terraform / APF |
| Platform RBAC | Terraform / APF |
| Azure Policy definitions | EPAC |
| Azure Policy set definitions | EPAC |
| Azure Policy assignments | EPAC |
| Azure Policy exemptions | EPAC |
| Policy-assignment role requirements | EPAC |

Terraform must not manage policy resources that are owned by EPAC.

## Source of truth

Policy content remains Azure-native JSON/JSONC wherever practical.

APF consumes the Microsoft Azure Landing Zones Library as an upstream,
versioned dependency and layers APF-specific policy configuration on top.

Pinned versions live in:

    foundation/policy/versions.json

## Desired-state strategy

APF uses two explicit desired-state modes:

- Brownfield adoption starts with `ownedOnly`.
- Greenfield targets `full` only after the intended policy baseline has been
  populated and reviewed.

A portal change is not a durable configuration change. A durable change must be
represented in source control.

## Migration baseline

The legacy HCI policy library is classified against the pinned ALZ/SLZ
releases. Legacy effects, enforcement modes and archetype placement are
migration inputs and must not be normalized away.

## Commit 14 — Scope-aware Audit-First Wave 1

The active profile is:

    foundation/policy/profiles/enterprise/audit-first-wave1.json

It contains four curated UPSTREAM assignments. Each assignment records:

- pinned upstream ALZ assignment name;
- legacy assignment name;
- legacy archetype;
- APF Level 1 scope key;
- policy definition ID and version;
- legacy enforcement mode;
- legacy effect/parameters.

The current mapping is:

    CAF-Deny-Public-IP      -> identity
    Deny-Classic-Resources  -> root
    Deny-Storage-http       -> landing_zones
    Deny-HybridNetworking   -> corp

The EPAC deployment root remains the APF root management group and desired state
remains:

    desiredState.strategy = ownedOnly

Commit 14 remains plan-only. There is no Policy Apply workflow.

Controls from the legacy `security` archetype are intentionally deferred until
APF defines an explicit scope model for that horizontal concern.

## Commit 15 — Protected Policy Apply

Commit 15 does not add policy content. It introduces the first Azure mutation
path for the reviewed Wave 1 desired state.

The generated customer workflow is:

    .github/workflows/policy-apply.yml

It is manual-only, restricted to `main`, uses the `apf-governance` GitHub
environment and authenticates with the Governance UAMI through OIDC.

Before deployment, EPAC rebuilds the plan from the current `main` branch. APF
then verifies that the plan contains only additive Policy Assignments already
represented in the generated Definitions tree. The guard rejects:

- Policy Assignment updates, replacements or deletes;
- Policy Definition changes;
- Policy Set Definition changes;
- Policy Exemption changes;
- Policy Enrollment changes;
- Role Assignment changes.

Only after that check may the workflow call:

    Deploy-PolicyPlan
    Deploy-RolesPlan

After deployment the workflow rebuilds the EPAC plan and requires zero
remaining policy and role changes.

This is deliberately narrower than the future steady-state apply capability.
DINE/Modify policies and role reconciliation are not enabled by Commit 15.
