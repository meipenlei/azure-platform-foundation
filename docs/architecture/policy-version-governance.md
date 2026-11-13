# Policy Version Governance

**Status:** Commit 17  
**Mutation:** none  
**Strategy:** `pinned_major`

APF treats an Azure Policy definition version as part of policy intent. Built-in definitions can change independently from APF, and a new major can contain breaking behavior. APF therefore uses explicit major pins such as `7.*.*`.

This allows minor and patch updates inside major 7 while preventing an automatic move to major 8.

The machine-readable contract is `foundation/policy/version-governance.json`; review records live under `foundation/policy/reviews/`.

## First review

Wave 2 pins `Kubernetes clusters should not allow container privilege escalation` to `7.*.*`. Azure exposes `8.0.0`, while pinned ALZ `2026.11.0` still references `7.*.*`. Commit 17 records a `hold` decision and changes no customer assignment.

The reviewed 7.2.0 -> 8.0.0 change includes a new Boolean `forcePrivilegeEscalationToBeFalse` parameter (default `false`), a Gatekeeper template change from `v3` to `v4`, and canonical effect values `Audit`, `Deny`, `Disabled`.

## Lifecycle

    EPAC reports newer major
        -> review record
        -> semantic/parameter comparison
        -> explicit test
        -> approval PR
        -> profile major-pin change
        -> EPAC plan / protected apply

Run `python tooling/policy/validate_versions.py`.
