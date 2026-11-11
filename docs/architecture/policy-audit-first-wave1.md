# Policy Audit-First Wave 1

**Status:** Commit 14  
**Execution:** Plan only  
**Desired state:** `ownedOnly`

## Purpose

Commit 14 is the first APF policy increment that expands beyond a single proof
assignment while preserving the original governance intent of the legacy HCI
library.

The key design rule is:

> Upstream equivalence does not erase legacy scope or enforcement semantics.

A policy that now exists in the current ALZ library is reused, but its legacy
APF behavior remains explicit when that behavior differs from upstream.

## Scope resolution

EPAC keeps the APF root management group as `deploymentRootScope`.

Individual assignments target Level 1 management groups resolved from:

    .foundation/level1-management-groups.yaml

The generator uses the Terraform-produced `management_group_ids` map and never
constructs management-group IDs from naming assumptions.

## Wave 1 mapping

| Legacy assignment | Current ALZ assignment | Legacy archetype | APF scope | Enforcement | Effect |
| --- | --- | --- | --- | --- | --- |
| `CAF-Deny-Public-IP` | `Deny-Public-IP` | `es_identity` | `identity` | `Default` | `Audit` |
| `Deny-Classic-Resources` | same | `es_root` | `root` | `DoNotEnforce` | `Deny` |
| `Deny-Storage-http` | same | `es_landing_zones` | `landing_zones` | `DoNotEnforce` | `Deny` |
| `Deny-HybridNetworking` | same | `es_corp` | `corp` | `DoNotEnforce` | `Deny` |

All four use built-in policy definitions and have no assignment identity.
Therefore Wave 1 is expected to produce no policy-assignment role changes.

## Why not the legacy security archetype yet?

`Deny-IP-forwarding` and `Deny-Public-IP-On-NIC` are good upstream candidates,
but the legacy library placed them in the horizontal `security` archetype.

The current Level 1 hierarchy has no `security` management group, and mapping
that archetype to `root`, `platform`, or `landing_zones` without an explicit
architecture decision would silently change governance scope.

Those controls are therefore deferred rather than guessed.

## Expected EPAC plan

For a customer where none of these assignments has been deployed yet:

    Policy Assignments:
      4 new

    Role Assignments:
      No changes required

    Deletes:
      0

The plan is reviewed before any policy apply capability is introduced.
