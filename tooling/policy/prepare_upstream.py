#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


REPOSITORY_URL = "https://github.com/Azure/Azure-Landing-Zones-Library.git"
REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_PATH = REPO_ROOT / "foundation" / "policy" / "versions.json"


class PrepareError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare pinned Azure Landing Zones Library checkouts for "
            "APF policy migration analysis."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Empty or non-existing directory used as the upstream cache root.",
    )
    return parser.parse_args()


def run(command: Sequence[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )
        raise PrepareError(
            f"Command failed ({result.returncode}): {' '.join(command)}"
            + (f"\n{detail}" if detail else "")
        )


def load_versions() -> dict:
    try:
        data = json.loads(VERSIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrepareError(f"Unable to read {VERSIONS_PATH}: {exc}") from exc
    return data


def clone_sparse(*, tag: str, sparse_path: str, destination: Path) -> None:
    if destination.exists():
        raise PrepareError(
            f"Destination already exists: {destination}. "
            "Use a fresh output directory; this tool never deletes existing data."
        )

    run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            tag,
            "--filter=blob:none",
            "--sparse",
            REPOSITORY_URL,
            str(destination),
        ]
    )
    run(
        [
            "git",
            "sparse-checkout",
            "set",
            sparse_path,
        ],
        cwd=destination,
    )


def main() -> int:
    args = parse_args()

    try:
        if shutil.which("git") is None:
            raise PrepareError("Required command 'git' was not found in PATH.")

        versions = load_versions()
        library = versions["azure_landing_zones_library"]
        alz_tag = str(library["alz_tag"])
        slz_tag = str(library["slz_tag"])

        args.output_dir.mkdir(parents=True, exist_ok=True)

        alz_dir = args.output_dir / "alz"
        slz_dir = args.output_dir / "slz"

        print(f"Preparing ALZ {alz_tag}...")
        clone_sparse(
            tag=alz_tag,
            sparse_path="platform/alz",
            destination=alz_dir,
        )

        print(f"Preparing SLZ {slz_tag}...")
        clone_sparse(
            tag=slz_tag,
            sparse_path="platform/slz",
            destination=slz_dir,
        )

        marker = {
            "schema_version": "0.1",
            "repository": REPOSITORY_URL,
            "alz": {
                "tag": alz_tag,
                "library_dir": str((alz_dir / "platform" / "alz").resolve()),
            },
            "slz": {
                "tag": slz_tag,
                "library_dir": str((slz_dir / "platform" / "slz").resolve()),
            },
        }
        (args.output_dir / "prepared.json").write_text(
            json.dumps(marker, indent=2) + "\n",
            encoding="utf-8",
        )

        print("[PASS] Pinned ALZ/SLZ libraries prepared.")
        print(f"ALZ: {alz_dir / 'platform' / 'alz'}")
        print(f"SLZ: {slz_dir / 'platform' / 'slz'}")
        return 0

    except (PrepareError, KeyError) as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
