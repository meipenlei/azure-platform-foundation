# Commit 11 — First EPAC Desired-State Plan

Suggested public commit message:

    feat: generate first policy desired state plan

## Scope

Commit 11 introduces the first executable APF policy desired state.

It is intentionally plan-only.

- adds the `enterprise/audit_first` subscription pilot profile;
- adds `tooling/customer-policy/configure.py`;
- generates deterministic EPAC customer files;
- uses the existing Plan UAMI for PR policy planning;
- uploads the EPAC plan as a GitHub Actions artifact;
- adds no Policy Apply workflow.

## First assignment

The pilot preserves legacy `CAF-Deny-Public-IP` behavior:

    effect = Audit
    enforcementMode = Default

The deployment root is the bootstrap subscription and desired state is:

    ownedOnly

## Public repository validation

    pip install -r tooling/customer-policy/requirements.txt

    python -m py_compile \
      tooling/customer-policy/configure.py \
      tooling/customer-policy/test_configure.py \
      tooling/policy/validate.py

    python -m unittest discover \
      -s tooling/customer-policy \
      -p "test_*.py"

    python tooling/policy/validate.py

## Generate lab04 desired state

Dry-run:

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

Generate:

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

Run the dry-run again. It should say the desired state is already generated.

## Validate through a lab04 pull request

Do not commit generated policy files directly to lab04 main.

    cd ../lab04-apf-azure-platform

    git switch -c apf/commit11-policy-plan

    git add \
      .foundation/policy.yaml \
      .github/workflows/policy-plan.yml \
      .gitignore \
      governance/policy

    git commit -m "feat: add APF policy desired state pilot"

    git push -u origin apf/commit11-policy-plan

    gh pr create \
      --base main \
      --head apf/commit11-policy-plan \
      --title "feat: add APF policy desired state pilot" \
      --body "Validate the first APF EPAC desired-state plan. No policy apply."

Expected workflow behavior:

- OIDC login uses `AZURE_PLAN_CLIENT_ID`;
- `Build-DeploymentPlans` runs;
- an EPAC plan artifact is uploaded;
- no Azure Policy resource is changed.

Do not merge the lab04 PR until the EPAC plan is reviewed.
