# APF Policy Tooling

This directory contains Governance-as-Code tooling for the APF policy layer.

## Commit 9 foundation

Commit 9 introduced the EPAC foundation, version pinning and ownership model.

## Commit 10 migration analysis

Commit 10 added pinned ALZ/SLZ preparation, migration classification and
semantic assignment-delta detection.

## Commit 11 desired-state pilot

Commit 11 introduces the first executable policy desired state without adding
an Apply path.

The APF profile is:

    foundation/policy/profiles/enterprise/
        audit-first-subscription-pilot.json

Customer generation is handled by:

    tooling/customer-policy/configure.py

The generated customer workflow uses the existing APF Plan identity and calls:

    Build-DeploymentPlans

It does not call:

    Deploy-PolicyPlan
    Deploy-RolesPlan

The privileged Governance identity is therefore not used for PR planning.

## EPAC and ALZ/SLZ versions

Versions remain pinned in:

    foundation/policy/versions.json

Commit 11 does not synchronize the full ALZ/SLZ assignment model into the
customer repository because APF Level 1 has not yet created the management
group hierarchy required by those archetypes.
