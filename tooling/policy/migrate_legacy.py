#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ASSET_TYPES = (
    "archetype_definitions",
    "policy_assignments",
    "policy_definitions",
    "policy_set_definitions",
    "role_definitions",
)

VALID_CLASSIFICATIONS = {
    "UPSTREAM",
    "APF_CUSTOM",
    "REVIEW",
    "OBSOLETE",
}

UPSTREAM_SUFFIXES = {
    "archetype_definitions": ".alz_archetype_definition.json",
    "policy_assignments": ".alz_policy_assignment.json",
    "policy_definitions": ".alz_policy_definition.json",
    "policy_set_definitions": ".alz_policy_set_definition.json",
    "role_definitions": ".alz_role_definition.json",
}


class MigrationError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a legacy ALZ-style policy library with pinned current "
            "ALZ/SLZ libraries and build an APF migration report."
        )
    )
    parser.add_argument("--legacy-library-dir", type=Path, required=True)
    parser.add_argument("--alz-library-dir", type=Path, required=True)
    parser.add_argument("--slz-library-dir", type=Path, required=True)
    parser.add_argument(
        "--mapping",
        type=Path,
        required=True,
        help="APF migration mapping/decision JSON.",
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    parser.add_argument(
        "--strict-counts",
        action="store_true",
        help="Fail when legacy asset counts differ from the mapping baseline.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError(f"Unable to parse JSON '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise MigrationError(f"JSON file '{path}' must contain an object.")
    return data


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: canonical(value[key])
            for key in sorted(value)
        }
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        canonical(value),
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_policy_reference(reference: Any) -> str | None:
    if not isinstance(reference, str) or not reference:
        return None

    match = re.search(
        r"/providers/Microsoft\.Authorization/"
        r"(policyDefinitions|policySetDefinitions)/([^/]+)$",
        reference,
        flags=re.IGNORECASE,
    )
    if match:
        return f"{match.group(1)}:{match.group(2)}"

    return reference


def parameter_values(properties: dict[str, Any]) -> dict[str, Any]:
    parameters = properties.get("parameters") or {}
    if not isinstance(parameters, dict):
        return {}

    result: dict[str, Any] = {}
    for name, value in parameters.items():
        if isinstance(value, dict) and "value" in value:
            result[name] = canonical(value["value"])
        else:
            result[name] = canonical(value)
    return result


def assignment_signature(doc: dict[str, Any]) -> dict[str, Any]:
    properties = doc.get("properties") or {}
    if not isinstance(properties, dict):
        properties = {}

    identity = doc.get("identity") or {}
    if not isinstance(identity, dict):
        identity = {}

    return {
        "policy_reference": normalize_policy_reference(
            properties.get("policyDefinitionId")
        ),
        "definition_version": properties.get("definitionVersion"),
        "enforcement_mode": properties.get("enforcementMode") or "Default",
        "identity_type": identity.get("type") or "None",
        "parameters": parameter_values(properties),
    }


def assignment_delta(
    legacy: dict[str, Any],
    upstream: dict[str, Any],
) -> dict[str, Any]:
    left = assignment_signature(legacy)
    right = assignment_signature(upstream)

    changed = [
        key
        for key in left
        if left[key] != right[key]
    ]

    preserve = [
        key
        for key in (
            "policy_reference",
            "enforcement_mode",
            "identity_type",
            "parameters",
        )
        if key in changed
    ]

    return {
        "legacy": left,
        "upstream": right,
        "changed_fields": changed,
        "preserve_legacy_fields": preserve,
        "requires_overlay": bool(preserve),
    }


def definition_signature(doc: dict[str, Any]) -> dict[str, Any]:
    properties = doc.get("properties") or {}
    if not isinstance(properties, dict):
        properties = {}
    return {
        "mode": properties.get("mode"),
        "parameters": canonical(properties.get("parameters") or {}),
        "policyRule": canonical(properties.get("policyRule") or {}),
    }


def policy_set_signature(doc: dict[str, Any]) -> dict[str, Any]:
    properties = doc.get("properties") or {}
    if not isinstance(properties, dict):
        properties = {}

    definitions = []
    for item in properties.get("policyDefinitions") or []:
        if not isinstance(item, dict):
            continue
        item_copy = dict(item)
        item_copy["policyDefinitionId"] = normalize_policy_reference(
            item_copy.get("policyDefinitionId")
        )
        definitions.append(canonical(item_copy))

    return {
        "parameters": canonical(properties.get("parameters") or {}),
        "policyDefinitions": definitions,
    }


def generic_semantic_delta(
    asset_type: str,
    legacy: dict[str, Any],
    upstream: dict[str, Any],
) -> dict[str, Any]:
    if asset_type == "policy_definitions":
        left = definition_signature(legacy)
        right = definition_signature(upstream)
    elif asset_type == "policy_set_definitions":
        left = policy_set_signature(legacy)
        right = policy_set_signature(upstream)
    else:
        return {}

    return {
        "semantic_equal": left == right,
        "legacy_hash": canonical_hash(left),
        "upstream_hash": canonical_hash(right),
    }


def extract_design_signals(doc: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, dict):
        return {}

    properties = doc.get("properties") or {}
    if not isinstance(properties, dict):
        return {}

    signals: dict[str, Any] = {}

    enforcement = properties.get("enforcementMode")
    if enforcement:
        signals["enforcement_mode"] = enforcement

    effects: dict[str, Any] = {}
    for name, value in parameter_values(properties).items():
        if "effect" in name.lower():
            effects[name] = value

    if effects:
        signals["effect_parameters"] = effects

    return signals


def legacy_asset_name(
    asset_type: str,
    doc: dict[str, Any],
) -> str | None:
    if asset_type == "role_definitions":
        properties = doc.get("properties") or {}
        if isinstance(properties, dict) and properties.get("roleName"):
            return str(properties["roleName"])
    if doc.get("name"):
        return str(doc["name"])
    return None


def load_legacy_assets(
    library_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {
        asset_type: []
        for asset_type in ASSET_TYPES
    }

    for asset_type in ASSET_TYPES:
        directory = library_dir / asset_type
        if not directory.is_dir():
            raise MigrationError(
                f"Missing legacy asset directory: {directory}"
            )

        for path in sorted(directory.glob("*.json")):
            if path.name.lower() == "readme.md":
                continue

            doc = load_json(path)

            if asset_type == "archetype_definitions":
                if isinstance(doc.get("name"), str):
                    result[asset_type].append(
                        {
                            "name": str(doc["name"]),
                            "path": str(path),
                            "doc": doc,
                        }
                    )
                    continue

                for name, value in doc.items():
                    if not isinstance(value, dict):
                        continue
                    archetype_doc = dict(value)
                    archetype_doc["name"] = name
                    result[asset_type].append(
                        {
                            "name": name,
                            "path": str(path),
                            "doc": archetype_doc,
                        }
                    )
                continue

            name = legacy_asset_name(asset_type, doc)
            if not name:
                raise MigrationError(
                    f"Unable to determine asset name for {path}"
                )

            result[asset_type].append(
                {
                    "name": name,
                    "path": str(path),
                    "doc": doc,
                }
            )

    return result


def load_upstream_assets(
    library_dir: Path,
    source: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {
        asset_type: {}
        for asset_type in ASSET_TYPES
    }

    for asset_type in ASSET_TYPES:
        directory = library_dir / asset_type
        if not directory.is_dir():
            continue

        suffix = UPSTREAM_SUFFIXES[asset_type]
        for path in sorted(directory.glob(f"*{suffix}")):
            doc = load_json(path)
            name = legacy_asset_name(asset_type, doc)
            if not name:
                raise MigrationError(
                    f"Unable to determine upstream asset name for {path}"
                )

            result[asset_type][name] = {
                "name": name,
                "source": source,
                "path": str(path),
                "doc": doc,
            }

    return result


def merge_upstream(
    alz: dict[str, dict[str, dict[str, Any]]],
    slz: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    merged: dict[str, dict[str, list[dict[str, Any]]]] = {
        asset_type: {}
        for asset_type in ASSET_TYPES
    }

    for asset_type in ASSET_TYPES:
        names = set(alz[asset_type]) | set(slz[asset_type])
        for name in names:
            items = []
            if name in alz[asset_type]:
                items.append(alz[asset_type][name])
            if name in slz[asset_type]:
                items.append(slz[asset_type][name])
            merged[asset_type][name] = items

    return merged


def resolve_upstream(
    *,
    asset_type: str,
    target: str,
    preferred_source: str | None,
    upstream: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any] | None:
    candidates = upstream[asset_type].get(target, [])
    if not candidates:
        return None

    if preferred_source:
        for candidate in candidates:
            if candidate["source"] == preferred_source:
                return candidate
        return None

    if len(candidates) == 1:
        return candidates[0]

    for source in ("alz", "slz"):
        for candidate in candidates:
            if candidate["source"] == source:
                return candidate

    return candidates[0]


def normalize_archetype_members(
    doc: dict[str, Any],
    mapping: dict[str, Any],
) -> dict[str, list[str]]:
    alias_sections = mapping.get("aliases", {})

    output: dict[str, list[str]] = {}
    for asset_type, field in (
        ("policy_assignments", "policy_assignments"),
        ("policy_definitions", "policy_definitions"),
        ("policy_set_definitions", "policy_set_definitions"),
        ("role_definitions", "role_definitions"),
    ):
        aliases = alias_sections.get(asset_type, {})
        values = doc.get(field) or []
        normalized = []
        for value in values:
            alias = aliases.get(value)
            if isinstance(alias, dict):
                normalized.append(str(alias.get("target", value)))
            else:
                normalized.append(str(value))
        output[field] = sorted(set(normalized))
    return output


def archetype_delta(
    legacy: dict[str, Any],
    upstream: dict[str, Any],
    mapping: dict[str, Any],
) -> dict[str, Any]:
    left = normalize_archetype_members(legacy, mapping)
    right = normalize_archetype_members(upstream, mapping)

    fields: dict[str, Any] = {}
    for key in left:
        legacy_only = sorted(set(left[key]) - set(right[key]))
        upstream_only = sorted(set(right[key]) - set(left[key]))
        if legacy_only or upstream_only:
            fields[key] = {
                "legacy_only": legacy_only,
                "upstream_only": upstream_only,
            }

    return {
        "requires_overlay": bool(fields),
        "membership_delta": fields,
    }


def validate_mapping(
    mapping: dict[str, Any],
) -> None:
    manual = mapping.get("manual_classifications", {})
    for asset_type, decisions in manual.items():
        if asset_type not in ASSET_TYPES:
            raise MigrationError(
                f"Unknown asset type in manual classifications: {asset_type}"
            )
        if not isinstance(decisions, dict):
            raise MigrationError(
                f"Manual classifications for {asset_type} must be an object."
            )
        for name, decision in decisions.items():
            classification = decision.get("classification")
            if classification not in VALID_CLASSIFICATIONS:
                raise MigrationError(
                    f"Invalid classification for {asset_type}/{name}: "
                    f"{classification}"
                )


def classify_asset(
    *,
    asset_type: str,
    asset: dict[str, Any],
    mapping: dict[str, Any],
    upstream: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    name = asset["name"]
    manual = (
        mapping
        .get("manual_classifications", {})
        .get(asset_type, {})
        .get(name)
    )

    if isinstance(manual, dict):
        result = {
            "asset_type": asset_type,
            "legacy_name": name,
            "legacy_path": asset["path"],
            "classification": manual["classification"],
            "match_kind": "manual",
            "reason": manual.get("reason"),
            "candidates": manual.get("candidates", []),
            "design_signals": extract_design_signals(asset["doc"]),
        }
        return result

    alias = (
        mapping
        .get("aliases", {})
        .get(asset_type, {})
        .get(name)
    )

    target = name
    source = None
    match_kind = "exact"

    if isinstance(alias, dict):
        target = str(alias["target"])
        source = alias.get("source")
        match_kind = "alias"

    match = resolve_upstream(
        asset_type=asset_type,
        target=target,
        preferred_source=source,
        upstream=upstream,
    )

    if match is None:
        return {
            "asset_type": asset_type,
            "legacy_name": name,
            "legacy_path": asset["path"],
            "classification": "REVIEW",
            "match_kind": "unresolved",
            "reason": "No current upstream match or explicit migration decision.",
            "design_signals": extract_design_signals(asset["doc"]),
        }

    result = {
        "asset_type": asset_type,
        "legacy_name": name,
        "legacy_path": asset["path"],
        "classification": "UPSTREAM",
        "match_kind": match_kind,
        "upstream": {
            "source": match["source"],
            "name": match["name"],
            "path": match["path"],
        },
        "design_signals": extract_design_signals(asset["doc"]),
    }

    if asset_type == "policy_assignments":
        result["delta"] = assignment_delta(
            asset["doc"],
            match["doc"],
        )
    elif asset_type in {
        "policy_definitions",
        "policy_set_definitions",
    }:
        result["delta"] = generic_semantic_delta(
            asset_type,
            asset["doc"],
            match["doc"],
        )
    elif asset_type == "archetype_definitions":
        result["delta"] = archetype_delta(
            asset["doc"],
            match["doc"],
            mapping,
        )

    return result


def build_report(
    *,
    legacy_library_dir: Path,
    alz_library_dir: Path,
    slz_library_dir: Path,
    mapping_path: Path,
    strict_counts: bool,
) -> dict[str, Any]:
    mapping = load_json(mapping_path)
    validate_mapping(mapping)

    legacy = load_legacy_assets(legacy_library_dir)
    alz = load_upstream_assets(alz_library_dir, "alz")
    slz = load_upstream_assets(slz_library_dir, "slz")
    upstream = merge_upstream(alz, slz)

    actual_counts = {
        asset_type: len(legacy[asset_type])
        for asset_type in ASSET_TYPES
    }

    expected_counts = (
        mapping
        .get("source", {})
        .get("expected_counts", {})
    )

    if strict_counts and expected_counts:
        mismatches = {
            key: {
                "expected": expected_counts.get(key),
                "actual": actual_counts.get(key),
            }
            for key in ASSET_TYPES
            if expected_counts.get(key) != actual_counts.get(key)
        }
        if mismatches:
            raise MigrationError(
                "Legacy asset counts do not match the migration baseline: "
                + json.dumps(mismatches, sort_keys=True)
            )

    assets = []
    for asset_type in ASSET_TYPES:
        for asset in legacy[asset_type]:
            assets.append(
                classify_asset(
                    asset_type=asset_type,
                    asset=asset,
                    mapping=mapping,
                    upstream=upstream,
                )
            )

    class_counts = Counter(
        item["classification"]
        for item in assets
    )

    type_counts: dict[str, dict[str, int]] = {}
    for asset_type in ASSET_TYPES:
        counter = Counter(
            item["classification"]
            for item in assets
            if item["asset_type"] == asset_type
        )
        type_counts[asset_type] = {
            classification: counter.get(classification, 0)
            for classification in sorted(VALID_CLASSIFICATIONS)
        }

    upstream_assignments = [
        item
        for item in assets
        if item["asset_type"] == "policy_assignments"
        and item["classification"] == "UPSTREAM"
    ]
    upstream_assignment_exact = sum(
        1
        for item in upstream_assignments
        if item["match_kind"] == "exact"
    )
    upstream_assignment_alias = sum(
        1
        for item in upstream_assignments
        if item["match_kind"] == "alias"
    )
    upstream_assignment_overlays = sum(
        1
        for item in upstream_assignments
        if item.get("delta", {}).get("requires_overlay")
    )

    return {
        "schema_version": "0.1",
        "source": mapping.get("source", {}),
        "upstream": mapping.get("upstream", {}),
        "counts": {
            "legacy": actual_counts,
            "classification": {
                key: class_counts.get(key, 0)
                for key in sorted(VALID_CLASSIFICATIONS)
            },
            "by_asset_type": type_counts,
            "policy_assignment_upstream_matches": {
                "exact": upstream_assignment_exact,
                "alias": upstream_assignment_alias,
                "total": len(upstream_assignments),
                "requiring_overlay": upstream_assignment_overlays,
            },
        },
        "assets": sorted(
            assets,
            key=lambda item: (
                item["asset_type"],
                item["legacy_name"].lower(),
            ),
        ),
    }


def markdown_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def write_markdown(report: dict[str, Any], path: Path) -> None:
    class_counts = report["counts"]["classification"]
    assignment_counts = report["counts"]["policy_assignment_upstream_matches"]

    lines = [
        "# HCI Foundation Policy Migration Report",
        "",
        "> Generated by `tooling/policy/migrate_legacy.py`. "
        "This report is analysis only and does not deploy Azure resources.",
        "",
        "## Summary",
        "",
        "| Classification | Count |",
        "| --- | ---: |",
    ]

    for classification in (
        "UPSTREAM",
        "APF_CUSTOM",
        "REVIEW",
        "OBSOLETE",
    ):
        lines.append(
            f"| {classification} | "
            f"{class_counts.get(classification, 0)} |"
        )

    lines.extend(
        [
            "",
            "## Policy assignment upstream matching",
            "",
            f"- Exact current upstream assignment names: "
            f"{assignment_counts['exact']}",
            f"- Curated high-confidence aliases: "
            f"{assignment_counts['alias']}",
            f"- Total upstream assignment candidates: "
            f"{assignment_counts['total']}",
            f"- Upstream candidates requiring an APF overlay: "
            f"{assignment_counts['requiring_overlay']}",
            "",
            "An upstream match does **not** mean the legacy APF behavior can be "
            "discarded. Enforcement mode, identity and parameter deltas are "
            "captured so that audit-first and Brownfield decisions remain visible.",
            "",
        ]
    )

    for asset_type in ASSET_TYPES:
        items = [
            item
            for item in report["assets"]
            if item["asset_type"] == asset_type
        ]
        lines.extend(
            [
                f"## {asset_type}",
                "",
                "| Legacy asset | Classification | Current upstream | Action |",
                "| --- | --- | --- | --- |",
            ]
        )

        for item in items:
            upstream = item.get("upstream")
            upstream_text = ""
            if upstream:
                upstream_text = (
                    f"{upstream['source']}:{upstream['name']}"
                )

            action = item.get("reason") or ""
            delta = item.get("delta", {})
            if delta.get("requires_overlay"):
                changed = ", ".join(
                    delta.get("changed_fields", [])
                    or delta.get("membership_delta", {}).keys()
                )
                action = (
                    "Preserve APF overlay"
                    + (f" ({changed})" if changed else "")
                )

            lines.append(
                "| "
                + " | ".join(
                    (
                        markdown_cell(item["legacy_name"]),
                        markdown_cell(item["classification"]),
                        markdown_cell(upstream_text),
                        markdown_cell(action),
                    )
                )
                + " |"
            )

        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    try:
        report = build_report(
            legacy_library_dir=args.legacy_library_dir,
            alz_library_dir=args.alz_library_dir,
            slz_library_dir=args.slz_library_dir,
            mapping_path=args.mapping,
            strict_counts=args.strict_counts,
        )

        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )

        write_markdown(report, args.output_markdown)

        counts = report["counts"]["classification"]
        print("APF legacy policy migration analysis")
        print("------------------------------------")
        for classification in (
            "UPSTREAM",
            "APF_CUSTOM",
            "REVIEW",
            "OBSOLETE",
        ):
            print(
                f"{classification:12} "
                f"{counts.get(classification, 0):>4}"
            )

        assignment = report["counts"]["policy_assignment_upstream_matches"]
        print()
        print(
            "Policy assignment upstream matches: "
            f"{assignment['total']} "
            f"({assignment['exact']} exact, {assignment['alias']} aliases)"
        )
        print(f"[PASS] JSON report: {args.output_json}")
        print(f"[PASS] Markdown report: {args.output_markdown}")
        return 0

    except MigrationError as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
