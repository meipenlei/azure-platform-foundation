# Azure Platform Foundation Policy Layer

APF separates Terraform-owned platform structure from EPAC-owned policy resources.

Commit 13 moves the active plan-only pilot to the APF root management group. The active profile is:

    foundation/policy/profiles/enterprise/
        audit-first-management-group-pilot.json

The customer deployment root is derived from:

    .foundation/level1-management-groups.yaml

It is not hard-coded in the product profile.

The pilot still contains one audit-only Public IP assignment and preserves:

    definitionVersion = 2.*.*
    effect = Audit
    enforcementMode = Default
    desiredState.strategy = ownedOnly

There is still no Policy Apply workflow.
