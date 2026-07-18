#!/usr/bin/env python3
"""Generate an Ed25519 signing key and a public trust-registry key record.

The private key must be stored outside the Gas Ratio Pro source/release tree.
Only the public key record belongs in an approved trust registry.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives.serialization import (  # noqa: E402
    BestAvailableEncryption,
    NoEncryption,
    PrivateFormat,
    Encoding,
)

from core.calibration_package_trust_contract import build_trust_key_record  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-key-output", type=Path, required=True)
    parser.add_argument("--public-record-output", type=Path, required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--project-id", action="append", required=True, dest="project_ids")
    parser.add_argument("--environment", action="append", choices=("validation", "production"), dest="environments")
    parser.add_argument("--valid-from", default="")
    parser.add_argument("--valid-until", default="")
    parser.add_argument("--password-env", default="", help="Environment variable containing the PEM password.")
    args = parser.parse_args()

    private_path = args.private_key_output.resolve()
    try:
        private_path.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise SystemExit("Refusing to write a private key inside the Gas Ratio Pro project tree")

    password = os.environ.get(args.password_env, "").encode("utf-8") if args.password_env else b""
    encryption = BestAvailableEncryption(password) if password else NoEncryption()
    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, encryption)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(pem)
    try:
        private_path.chmod(0o600)
    except OSError:
        pass

    record = build_trust_key_record(
        key_id=args.key_id,
        public_key=private_key.public_key(),
        owner=args.owner,
        organization_id=args.organization_id,
        allowed_projects=tuple(args.project_ids),
        allowed_environments=tuple(args.environments or ("validation", "production")),
        valid_from=args.valid_from or None,
        valid_until=args.valid_until or None,
    )
    args.public_record_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_record_output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Private key: {private_path}")
    print(f"Public registry record: {args.public_record_output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
