# Commit 15 — Protected EPAC Policy Apply

Suggested public commit:

    feat: add protected policy apply workflow

## Scope

Commit 15 changes execution capability only. The four Audit-First Wave 1
assignments remain unchanged.

The customer generator now produces:

    .github/workflows/policy-plan.yml
    .github/workflows/policy-apply.yml
    governance/policy/tooling/verify_apply_plan.py

The apply workflow is manual-only, main-only, uses the `apf-governance`
environment and authenticates with `AZURE_GOVERNANCE_CLIENT_ID`.

Before any Azure mutation it rebuilds the EPAC plan and rejects anything except
new Policy Assignments already represented by the generated Definitions tree.
It then deploys policy resources, runs the roles deployment stage, rebuilds the
plan and requires zero remaining changes.

## Validate the public repository

    pip install -r tooling/customer-policy/requirements.txt

    python -m py_compile \
      tooling/customer-policy/configure.py \
      tooling/customer-policy/verify_apply_plan.py \
      tooling/customer-policy/test_configure.py \
      tooling/customer-policy/test_verify_apply_plan.py

    python -m unittest discover \
      -s tooling/customer-policy \
      -p "test_*.py"

    python tooling/policy/validate.py

## Commit public changes

    git add \
      .github/workflows/policy-foundation-smoke.yml \
      foundation/policy/README.md \
      docs/architecture/policy-protected-apply.md \
      tooling/customer-policy

    git commit -m "feat: add protected policy apply workflow"
    git push origin main

## Generate lab04

Start from the merged Commit 14 main branch:

    cd ~/GIT/Repos/lab04-apf-azure-platform
    git switch main
    git pull
    git switch -c apf/commit15-policy-protected-apply

Then from the APF repository:

    cd ~/GIT/Repos/azure-platform-foundation

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

The last command must report that the desired state is already generated.

The customer diff should add the protected apply workflow and generated apply
guard. The four policy assignment Definitions must not change semantically.

## Customer PR

    cd ~/GIT/Repos/lab04-apf-azure-platform

    git add \
      .foundation/policy.yaml \
      .github/workflows/policy-plan.yml \
      .github/workflows/policy-apply.yml \
      governance/policy

    git commit -m "feat: add protected policy apply workflow"
    git push -u origin apf/commit15-policy-protected-apply

    gh pr create \
      --base main \
      --head apf/commit15-policy-protected-apply \
      --title "feat: add protected policy apply workflow" \
      --body "Add the first protected EPAC policy apply path. Policy content is unchanged; apply is additive-only and guarded."

Because the Wave 1 assignments have not yet been deployed, the PR plan is
expected to continue showing:

    Policy Assignments: 4 new
    Role Assignments:   No changes required
    Deletes:            0

Merge the PR only after that plan is green.

## First real Policy Apply

After the customer PR is merged, dispatch the workflow from `main`:

    gh workflow run policy-apply.yml \
      --ref main \
      -f confirm_apply=true

The expected pre-apply safety output is:

    [PASS] EPAC protected apply boundary verified.
    [PASS] Allowed new policy assignments: 4.
    [PASS] Role assignment changes: 0.

EPAC should then create the four reviewed Policy Assignments.

The roles stage has no planned changes in Commit 15 and should skip/no-op.

Finally, the workflow rebuilds the plan. Expected convergence:

    Policy deployment stage skipped - no changes detected
    Role assignment stage skipped - no changes detected

    [PASS] EPAC post-apply convergence verified.
    [PASS] Remaining policy changes: 0.
    [PASS] Remaining role changes: 0.

Do not expand the desired state or add DINE/Modify controls in this commit.
