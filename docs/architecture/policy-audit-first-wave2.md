# Policy Audit-First Wave 2

**Status:** Commit 16  
**Execution:** PR plan + protected manual apply  
**Desired state:** `ownedOnly`  
**Upstream:** `Azure/Azure-Landing-Zones-Library` pinned at `platform/alz/2026.11.0`

## Purpose

Commit 16 expands the proven Wave 1 desired state without changing the
execution security boundary introduced by Commit 15.

The selection rule is intentionally narrow:

- the legacy assignment is classified as an upstream-aligned control;
- the pinned ALZ library still contains the corresponding assignment;
- the assignment references an Azure built-in Policy or Policy Set;
- no managed identity is required;
- no Policy Assignment role changes are required;
- legacy `Audit` and `DoNotEnforce` semantics are preserved;
- no REVIEW-classified asset is introduced.

This keeps the change inside the already-proven additive-only apply boundary.

## Cumulative desired state

Wave 2 is cumulative. The four Wave 1 assignments remain unchanged and four
new assignments are added.

| Wave | Upstream / legacy assignment | APF Level 1 scope | Semantics |
| ---: | --- | --- | --- |
| 1 | `CAF-Deny-Public-IP` / `Deny-Public-IP` | Identity | `Audit` |
| 1 | `Deny-Classic-Resources` | Root | `DoNotEnforce`, effect `Deny` |
| 1 | `Deny-Storage-http` | Landing Zones | `DoNotEnforce`, effect `Deny` |
| 1 | `Deny-HybridNetworking` | Corp | `DoNotEnforce`, effect `Deny` |
| 2 | `Audit-ResourceRGLocation` | Root | built-in audit |
| 2 | `Audit-AppGW-WAF` | Landing Zones | effect `Audit` |
| 2 | `Deny-Priv-Esc-AKS` | Landing Zones | `DoNotEnforce`, effect `Deny` |
| 2 | `Deny-Privileged-AKS` | Landing Zones | `DoNotEnforce`, effect `Deny` |

The active profile is:

    foundation/policy/profiles/enterprise/audit-first-wave2.json

## Inheritance-aware deduplication

The legacy `Audit-AppGW-WAF` assignment was present in both
`es_landing_zones` and `es_online`.

APF Level 1 places `Online` below `Landing Zones`. Assigning the same policy
again at `Online` would duplicate the assignment while adding no effective
coverage. Commit 16 therefore creates one assignment at `Landing Zones` and
lets Azure Policy inheritance cover both `Corp` and `Online` descendants.

The profile records the collapsed legacy `es_online` membership so the
migration decision remains explicit and reviewable.

## Deliberately deferred controls

Commit 16 does not add:

- custom ALZ Policy Definitions or Policy Set Definitions;
- `DINE` or `Modify` assignments;
- assignments that require managed identities or role reconciliation;
- sovereignty/confidential controls;
- REVIEW-classified migration assets;
- the preview `Audit-ZoneResiliency` built-in initiative;
- legacy horizontal `security` archetype assignments until APF defines their
  explicit scope model.

Those are separate capability increments rather than hidden side effects of a
baseline expansion.

## Apply behavior

The existing Commit 15 workflow remains unchanged in principle:

    pull request -> Plan UAMI -> Build-DeploymentPlans

After merge:

    workflow_dispatch on main
      -> apf-governance
      -> Governance UAMI
      -> fresh EPAC plan
      -> additive-only APF guard
      -> Deploy-PolicyPlan
      -> bounded post-apply convergence check

For a Wave-1-converged environment, the expected Commit 16 PR plan is:

    Policy Assignments: 4 new
    Role Assignments:   0 changes
    Deletes:            0

The four existing Wave 1 Policy Assignment payloads are intentionally kept
byte-stable by preserving their original Wave 1 node and stage metadata.
