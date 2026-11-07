#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_ROOT = REPO_ROOT / "foundation" / "policy"


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{path} must contain a JSON object.")
    return data


def validate_versions() -> None:
    versions = load_json(POLICY_ROOT / "versions.json")

    epac = versions.get("epac", {})
    if epac.get("module") != "EnterprisePolicyAsCode":
        raise ValidationError("Unexpected EPAC module name.")
    if not epac.get("version"):
        raise ValidationError("EPAC version must be pinned.")

    alz = versions.get("azure_landing_zones_library", {})
    for key in ("alz_tag", "slz_tag"):
        value = str(alz.get(key, ""))
        if not value.startswith("platform/"):
            raise ValidationError(f"{key} must be a pinned platform tag.")

    desired = versions.get("desired_state", {})
    if desired.get("brownfield_default") != "ownedOnly":
        raise ValidationError(
            "Brownfield default must remain ownedOnly."
        )
    if desired.get("greenfield_target") != "full":
        raise ValidationError(
            "Greenfield target must be explicit full ownership."
        )


def validate_global_settings_template() -> None:
    path = (
        POLICY_ROOT
        / "templates"
        / "global-settings.jsonc.j2"
    )
    content = path.read_text(encoding="utf-8")

    required_tokens = (
        "[[ pac_owner_id ]]",
        "[[ pac_selector ]]",
        "[[ azure_cloud ]]",
        "[[ tenant_id ]]",
        "[[ deployment_root_scope ]]",
        "[[ managed_identity_location ]]",
        "[[ desired_state_strategy ]]",
    )

    missing = [
        token
        for token in required_tokens
        if token not in content
    ]

    if missing:
        raise ValidationError(
            "global-settings template is missing: "
            + ", ".join(missing)
        )

    if '"strategy": "full"' in content:
        raise ValidationError(
            "global-settings template must not hard-code full ownership."
        )


def validate_library_json() -> None:
    library = POLICY_ROOT / "library" / "apf"
    for path in library.rglob("*.json"):
        load_json(path)


def main() -> int:
    try:
        validate_versions()
        validate_global_settings_template()
        validate_library_json()
        print("[PASS] APF policy foundation validation.")
        return 0
    except (ValidationError, OSError) as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
