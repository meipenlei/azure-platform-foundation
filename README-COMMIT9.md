# Commit 9 — Governance as Code Foundation

Suggested commit message:

    feat: introduce governance as code foundation

## What this commit changes

1. Adds `Resource Policy Contributor` to the existing APF governance UAMI.
2. Pins EPAC `EnterprisePolicyAsCode` to `11.5.11`.
3. Pins ALZ and SLZ library releases to `2026.11.0`.
4. Introduces the APF Policy product structure.
5. Documents Governance-as-Code ownership and desired-state semantics.
6. Adds read-only legacy policy inventory tooling.
7. Adds guarded EPAC plan/apply wrappers for future customer integration.
8. Adds a public CI smoke test that installs the pinned EPAC module.

## What this commit deliberately does not do

- It does not deploy any Azure Policy definition, initiative, assignment or
  exemption.
- It does not enable EPAC `full` ownership against any customer environment.
- It does not bulk-copy the old HCI policy library.
- It does not change customer-init yet.

## Local validation

From the APF repository:

    python -m py_compile       tooling/policy/inventory.py       tooling/policy/validate.py       tooling/policy/test_inventory.py

    python -m unittest discover       -s tooling/policy       -p "test_*.py"

    python tooling/policy/validate.py

If PowerShell 7.4+ is installed:

    pwsh ./tooling/policy/Install-Epac.ps1

## Optional legacy inventory

If the old repository is checked out beside APF:

    python tooling/policy/inventory.py       --library-dir ../hci-foundation01/configuration/level1/alz/es/lib       --output-json /tmp/hci-policy-inventory.json

Expected top-level counts:

    archetype_definitions       14
    policy_assignments          91
    policy_definitions           3
    policy_set_definitions       2
    role_definitions             1

## After push

Let `policy-foundation-smoke.yml` complete successfully.

Then rerun the existing Level 0 governance lifecycle against `lab04`. The only
expected Azure change is one new subscription-scope role assignment:

    Resource Policy Contributor

for the existing governance managed identity.

Do not run EPAC apply against `lab04` in Commit 9.
