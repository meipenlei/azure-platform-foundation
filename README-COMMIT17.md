# Commit 17 — Policy Version Governance

Copy the package contents over the APF repository root, then run:

    python apply_commit17.py

    python -m py_compile \
      tooling/policy/validate_versions.py \
      tooling/policy/test_validate_versions.py

    python -m unittest discover \
      -s tooling/policy \
      -p "test_*.py"

    python tooling/policy/validate.py
    python tooling/policy/validate_versions.py

Expected:

    [PASS] 8 assignment(s) use explicit major-version pins.
    [PASS] Major-version upgrades require explicit APF review records.
    [REVIEW] ... profile 7.*.*, latest observed 8.0.0, status=hold

Then commit the public repository only:

    git add \
      .github/workflows/policy-foundation-smoke.yml \
      foundation/policy/version-governance.json \
      foundation/policy/reviews \
      foundation/policy/README.md \
      docs/architecture/policy-version-governance.md \
      tooling/policy/validate_versions.py \
      tooling/policy/test_validate_versions.py

    git commit -m "feat: add policy version governance"
    git push origin main

Commit 17 intentionally requires no lab04 generator run and no policy apply.
