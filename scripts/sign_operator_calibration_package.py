#!/usr/bin/env python3
"""Create a detached Ed25519 signature for an immutable operator package."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.serialization import load_pem_private_key  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from core.calibration_package_trust_contract import build_detached_signature  # noqa: E402
from core.operator_calibration_package_contract import PACKAGE_MANIFEST_NAME, operator_package_fingerprint  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--signer-id", required=True)
    parser.add_argument("--signer-name", required=True)
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--expires-at", default="")
    parser.add_argument("--parent-package-fingerprint", default="")
    parser.add_argument("--lineage-relation", choices=("root", "supersedes", "derived_from", "recalibrated_from"), default="root")
    parser.add_argument("--lineage-reason", default="")
    parser.add_argument("--password-env", default="")
    args = parser.parse_args()

    with ZipFile(args.package, "r") as archive:
        manifest = json.loads(archive.read(PACKAGE_MANIFEST_NAME).decode("utf-8"))
    fingerprint = str(manifest.get("package_fingerprint", ""))
    if operator_package_fingerprint(manifest) != fingerprint:
        raise SystemExit("Operator package manifest fingerprint is invalid")

    password = os.environ.get(args.password_env, "").encode("utf-8") if args.password_env else None
    private_key = load_pem_private_key(args.private_key.read_bytes(), password=password)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise SystemExit("Private key is not Ed25519")
    envelope = build_detached_signature(
        private_key=private_key,
        package_fingerprint=fingerprint,
        key_id=args.key_id,
        project_id=args.project_id,
        signer_id=args.signer_id,
        signer_name=args.signer_name,
        organization_id=args.organization_id,
        expires_at=args.expires_at or None,
        parent_package_fingerprint=args.parent_package_fingerprint,
        lineage_relation=args.lineage_relation,
        lineage_reason=args.lineage_reason,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Detached signature: {args.output.resolve()}")
    print(f"Package fingerprint: {fingerprint}")
    print(f"Signature fingerprint: {envelope['signature_fingerprint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
