# HCI Foundation Policy Migration — Commit 10 Baseline

**Status:** Initial curated migration baseline  
**Azure impact:** None  
**Upstream baseline:** ALZ/SLZ `2026.11.0`

## Result

The legacy library contains 111 policy/governance assets in the five analyzed
asset classes.

Initial classification:

| Classification | Count |
| --- | ---: |
| UPSTREAM | 88 |
| APF_CUSTOM | 6 |
| REVIEW | 17 |
| OBSOLETE | 0 |
| **Total** | **111** |

No asset is automatically marked obsolete.

## Policy assignments

Of the 91 legacy policy assignments:

| Result | Count |
| --- | ---: |
| Exact assignment name in current ALZ | 63 |
| High-confidence curated rename to current ALZ | 11 |
| APF_CUSTOM | 4 |
| REVIEW | 13 |
| OBSOLETE | 0 |
| **Total** | **91** |

This gives 74 current upstream assignment candidates.

An `UPSTREAM` classification does not mean that the current ALZ assignment can
be consumed without an APF overlay. The migration tooling compares the legacy
and current assignment for:

- policy/initiative reference;
- `enforcementMode`;
- identity type;
- parameters;
- definition-version metadata.

This preserves the old framework's audit-first and Brownfield decisions.

### APF_CUSTOM assignment baseline

The initial APF-specific assignment set contains:

- `CAF-Deny-Subnet-No-Udr`
- `CAF-Deny-CompliantTag`
- `CAF-Modify-InheritTag`
- `Deny-Private-DNS-Zones`

For `CAF-Deny-Subnet-No-Udr` and `Deny-Private-DNS-Zones`, the current ALZ
policy definitions can be reused while APF retains its assignment semantics.

### Assignment review set

The initial review set contains 13 assignments, including:

- the two legacy Sovereignty baseline assignments;
- diagnostic-log and MDFC configuration assignments whose current ALZ models
  changed;
- ISO 27001:2013;
- the two custom VNet flow-log assignments;
- Linux/Windows/Microsoft security-baseline assignments;
- legacy AKS Policy and Guest Configuration assignments.

These are intentionally not copied or retired by Commit 10.

## Custom policy definitions

The three legacy custom definitions classify as:

- `CAF-Deny-Subnet-Without-Nsg` -> **UPSTREAM**
  (`Deny-Subnet-Without-Nsg`)
- `CAF-Deny-Subnet-Without-Udr` -> **UPSTREAM**
  (`Deny-Subnet-Without-Udr`)
- `CAF-Deploy-VNet-FlowLogs` -> **REVIEW**

## Custom policy set definitions

Both legacy policy sets remain **APF_CUSTOM** candidates:

- `CAF-Deny-CompliantTag`
- `CAF-Modify-InheritTag`

Their content will be modernized before entering the APF library.

## Archetypes

Twelve of fourteen legacy archetypes map directly or by a simple naming
translation to current ALZ/SLZ archetypes.

The two legacy confidential profiles remain **REVIEW**:

- `confidential-corp`
- `confidential-online`

They should be reconciled with the current SLZ L1/L2/L3 control hierarchy
instead of copied directly.

## Custom role

`CAF-network-vhub-peering` remains **REVIEW**.

It belongs to the connectivity/RBAC boundary and is therefore better evaluated
when APF Level 2 permissions are introduced.

## Next step

Commit 10 does not create an EPAC deployment structure yet.

The next bounded step should take the migration report and produce the first
APF policy overlay/profile:

1. consume the selected upstream ALZ assets;
2. preserve the audited parameter/enforcement deltas;
3. migrate the two APF tag initiatives;
4. keep all `REVIEW` assets disabled from deployment;
5. generate the first EPAC plan without applying it.
