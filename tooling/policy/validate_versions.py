#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_ROOT = REPO_ROOT / "foundation" / "policy"
GOVERNANCE_PATH = POLICY_ROOT / "version-governance.json"
MAJOR_WILDCARD = re.compile(r"^(?P<major>\d+)\.\*\.\*(?P<preview>-preview)?$")
FULL_VERSION = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?P<preview>-preview)?$")
VALID_REVIEW_STATUS = {"hold", "approved", "rejected"}

class VersionGovernanceError(RuntimeError):
    pass

def load_json(path: Path) -> dict[str, Any]:
    try: data=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise VersionGovernanceError(f"Unable to read JSON '{path}': {exc}") from exc
    if not isinstance(data,dict): raise VersionGovernanceError(f"JSON '{path}' must contain an object.")
    return data

def repository_path(value: str) -> Path:
    path=(REPO_ROOT/value).resolve()
    try: path.relative_to(REPO_ROOT.resolve())
    except ValueError as exc: raise VersionGovernanceError(f"Path escapes repository: {value}") from exc
    return path

def major_from_pin(value: str) -> int:
    m=MAJOR_WILDCARD.fullmatch(value)
    if not m: raise VersionGovernanceError(f"definition_version must pin one major as '#.*.*', got {value!r}.")
    return int(m.group('major'))

def major_from_version(value: str) -> int:
    m=FULL_VERSION.fullmatch(value)
    if not m: raise VersionGovernanceError(f"Observed version must be '#.#.#', got {value!r}.")
    return int(m.group('major'))

def profile_pins(profile: dict[str, Any]) -> tuple[dict[str,int],dict[str,str]]:
    assignments=profile.get('assignments')
    if not isinstance(assignments,list) or not assignments: raise VersionGovernanceError('Active profile must contain assignments.')
    by_definition:dict[str,int]={}; by_key:dict[str,str]={}
    for a in assignments:
        if not isinstance(a,dict): raise VersionGovernanceError('Every assignment must be an object.')
        key=a.get('key'); d=a.get('definition') or {}; did=d.get('id'); version=d.get('definition_version')
        if not isinstance(key,str) or not key: raise VersionGovernanceError('Every assignment needs a key.')
        if not isinstance(did,str) or not did.startswith('/providers/Microsoft.Authorization/'): raise VersionGovernanceError(f"Assignment {key!r} has invalid definition ID.")
        if not isinstance(version,str) or not version: raise VersionGovernanceError(f"Assignment {key!r} is missing definition_version.")
        major=major_from_pin(version); nid=did.lower()
        if nid in by_definition and by_definition[nid]!=major: raise VersionGovernanceError(f"Definition {did} uses conflicting majors.")
        by_definition[nid]=major; by_key[key]=version
    return by_definition,by_key

def validate_review(path: Path, review: dict[str,Any], pins_by_definition:dict[str,int], pins_by_key:dict[str,str]) -> str:
    did=review.get('policy_definition_id'); current_pin=review.get('current_pin'); latest=review.get('observed_latest'); status=review.get('status'); keys=review.get('assignment_keys')
    if status not in VALID_REVIEW_STATUS: raise VersionGovernanceError(f"Review {path} has invalid status {status!r}.")
    if not isinstance(did,str) or not isinstance(current_pin,str) or not isinstance(latest,str): raise VersionGovernanceError(f"Review {path} is incomplete.")
    if not isinstance(keys,list) or not keys: raise VersionGovernanceError(f"Review {path} must list assignment_keys.")
    current_major=major_from_pin(current_pin); latest_major=major_from_version(latest)
    if pins_by_definition.get(did.lower())!=current_major: raise VersionGovernanceError(f"Review {path} does not match active profile major.")
    for key in keys:
        if key not in pins_by_key or major_from_pin(pins_by_key[key])!=current_major: raise VersionGovernanceError(f"Review {path} references mismatched assignment key {key!r}.")
    if review.get('current_effective_major')!=current_major or review.get('observed_latest_major')!=latest_major: raise VersionGovernanceError(f"Review {path} major metadata is inconsistent.")
    if latest_major<=current_major: raise VersionGovernanceError(f"Review {path} does not describe a newer major.")
    if status=='hold' and review.get('decision')!='keep_current_major': raise VersionGovernanceError(f"Hold review {path} must keep current major.")
    if status=='approved':
        if review.get('decision')!='upgrade_major': raise VersionGovernanceError(f"Approved review {path} must approve an upgrade.")
        target=review.get('target_pin')
        if not isinstance(target,str) or major_from_pin(target)!=latest_major: raise VersionGovernanceError(f"Approved review {path} target_pin mismatch.")
    return f"{did}: profile {current_pin}, latest observed {latest}, status={status}"

def validate() -> tuple[int,list[str]]:
    g=load_json(GOVERNANCE_PATH)
    if g.get('strategy')!='pinned_major': raise VersionGovernanceError('Strategy must be pinned_major.')
    if g.get('definition_version_pattern')!='major_wildcard': raise VersionGovernanceError('definition_version_pattern must be major_wildcard.')
    expected={'built_in_major_upgrade':'explicit_review_required','minor_updates_within_pinned_major':'auto_ingest','patch_updates':'auto_ingest','preview_versions':'explicit_pin_and_review','missing_definition_version':'reject'}
    if g.get('rules')!=expected: raise VersionGovernanceError('Version-governance rules do not match APF contract.')
    profile=load_json(repository_path(g['active_profile']))
    pins_by_definition,pins_by_key=profile_pins(profile)
    records=g.get('review_records')
    if not isinstance(records,list): raise VersionGovernanceError('review_records must be an array.')
    summaries=[]
    for rel in records:
        if not isinstance(rel,str): raise VersionGovernanceError('Review path must be a string.')
        p=repository_path(rel); summaries.append(validate_review(p,load_json(p),pins_by_definition,pins_by_key))
    return len(pins_by_key),summaries

def main() -> int:
    try:
        count,summaries=validate(); print(f"[PASS] {count} assignment(s) use explicit major-version pins."); print('[PASS] Major-version upgrades require explicit APF review records.')
        for s in summaries: print(f"[REVIEW] {s}")
        return 0
    except (VersionGovernanceError,OSError,KeyError,TypeError) as exc:
        print(f"[ERROR] {exc}",file=sys.stderr); return 1

if __name__=='__main__': raise SystemExit(main())
