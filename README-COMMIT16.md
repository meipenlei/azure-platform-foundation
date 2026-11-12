# Commit 16 — Scope-aware Audit-First Wave 2

Commit 16 expands the APF Azure Policy desired state from four to eight
cumulative assignments while keeping the Commit 15 protected apply boundary
unchanged.

## New Wave 2 controls

| Assignment | APF scope | Semantics |
| --- | --- | --- |
| `Audit-ResourceRGLocation` | Root | built-in audit |
| `Audit-AppGW-WAF` | Landing Zones | effect `Audit` |
| `Deny-Priv-Esc-AKS` | Landing Zones | `DoNotEnforce`, effect `Deny` |
| `Deny-Privileged-AKS` | Landing Zones | `DoNotEnforce`, effect `Deny` |

All four are present in the pinned ALZ `platform/alz/2026.11.0` library, use
Azure built-ins, require no Policy Assignment identity and generate no Role
Assignment changes.

The legacy `Audit-AppGW-WAF` assignment existed at both Landing Zones and
Online. APF assigns it once at Landing Zones because Online is a child of that
management group and inherits the policy. The profile records this deliberate
migration deduplication.

Wave 1 assignment payloads are preserved byte-for-byte. This is required by
the current additive-only apply guard.

## 1. Apply to the public APF repository

Overlay this package on the repository root, then run:

    cd ~/GIT/Repos/azure-platform-foundation

    python -m py_compile \
      tooling/customer-policy/configure.py \
      tooling/customer-policy/test_configure.py \
      tooling/policy/validate.py

    python -m unittest discover \
      -s tooling/customer-policy \
      -p "test_*.py"

    python tooling/policy/validate.py

    git status
    git diff

Expected unit-test result:

    Ran 12 tests
    OK

Expected policy validation:

    [PASS] APF policy foundation validation.

Commit:

    git add \
      foundation/policy/profiles/enterprise/audit-first-wave2.json \
      foundation/policy/README.md \
      docs/architecture/policy-audit-first-wave2.md \
      tooling/customer-policy/configure.py \
      tooling/customer-policy/test_configure.py \
      tooling/policy/validate.py

    git commit -m "feat: add policy audit-first wave2"
    git push origin main

Do not commit `README-COMMIT16.md` unless you intentionally want the package
instructions in the repository.

## 2. Generate the lab04 customer change

Start from current main:

    cd ~/GIT/Repos/lab04-apf-azure-platform
    git switch main
    git pull
    git switch -c apf/commit16-policy-wave2

Dry-run from the APF repository:

    cd ~/GIT/Repos/azure-platform-foundation

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

Against a converged Commit 15 / Wave 1 customer, the dry-run should list
exactly these generated changes:

    governance/policy/README.md
    .foundation/policy.yaml
    governance/policy/Definitions/policyAssignments/apf-audit-resource-rg-location.assignment.jsonc
    governance/policy/Definitions/policyAssignments/apf-audit-appgw-waf.assignment.jsonc
    governance/policy/Definitions/policyAssignments/apf-deny-priv-esc-aks.assignment.jsonc
    governance/policy/Definitions/policyAssignments/apf-deny-privileged-aks.assignment.jsonc

No existing Wave 1 assignment file should be listed.

Write and verify idempotency:

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

Expected final output:

    [PASS] Customer policy desired state is already generated.

## 3. Customer PR

    cd ~/GIT/Repos/lab04-apf-azure-platform

    git status
    git diff

    git add \
      .foundation/policy.yaml \
      governance/policy

    git commit -m "feat: add APF policy audit-first wave2"
    git push -u origin apf/commit16-policy-wave2

    gh pr create \
      --base main \
      --head apf/commit16-policy-wave2 \
      --title "feat: add APF policy audit-first wave2" \
      --body "Add the second curated APF audit-first policy wave. Four built-in, identity-free assignments; protected additive apply remains unchanged."

Expected EPAC PR result:

    Policy Assignments:
      4 new
      4 unchanged

    Role Assignments:
      No changes required

    Deletes:
      0

Do not run the policy apply before the PR plan is reviewed and the PR is
merged.

## 4. Protected apply after merge

After the PR is green and merged:

    gh workflow run policy-apply.yml \
      --ref main \
      -f confirm_apply=true

Expected pre-apply guard:

    [PASS] EPAC protected apply boundary verified.
    [PASS] Allowed new policy assignments: 4.
    [PASS] Role assignment changes: 0.

Expected deployment: four new Policy Assignments only.

Expected post-apply result after bounded convergence retry if needed:

    [PASS] EPAC post-apply convergence verified.
    [PASS] Remaining policy changes: 0.
    [PASS] Remaining role changes: 0.

## Deferred from Commit 16

Commit 16 deliberately does not introduce DINE/Modify, assignment identities,
role reconciliation, custom ALZ definitions/sets, sovereignty controls,
REVIEW-classified assets, preview Zone Resiliency, or the unresolved legacy
horizontal `security` archetype scope.
