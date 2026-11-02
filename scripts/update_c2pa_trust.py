"""Refreshes the C2PA trust list embedded in the package.

Run before each release, never at analysis time (an analysis sends nothing
over the network):

    uv run python scripts/update_c2pa_trust.py

It downloads the official list of the C2PA conformance program
(https://github.com/c2pa-org/conformance-public, CC BY 4.0) at its latest
commit, writes src/talax/data/c2pa/, and prints which organisations were
added or removed, for the commit message and the release notes.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml

REPO = "c2pa-org/conformance-public"
OUT = Path(__file__).resolve().parent.parent / "src" / "talax" / "data" / "c2pa"
PEM = "C2PA-TRUST-LIST.pem"
_JSON = "C2PA-TRUST-LIST.json"  # only read for its dates and organisations


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "talax-update"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data: bytes = response.read()
    return data


def _organisations(lote: dict[str, Any]) -> list[str]:
    names = {
        entity["TrustedEntityInformation"]["TEName"][0]["value"]
        for entity in lote["TrustedEntitiesList"]
    }
    return sorted(names)


def main() -> None:
    commits = json.loads(
        _get(f"https://api.github.com/repos/{REPO}/commits?path=trust-list&per_page=1")
    )
    commit = commits[0]["sha"]
    raw = f"https://raw.githubusercontent.com/{REPO}/{commit}/trust-list"
    pem = _get(f"{raw}/{PEM}")
    lote = json.loads(_get(f"{raw}/{_JSON}"))["LoTE"]
    info = lote["ListAndSchemeInformation"]
    organisations = _organisations(lote)
    if b"BEGIN CERTIFICATE" not in pem or not organisations:
        sys.exit("the downloaded list looks empty: nothing written")

    source = OUT / "source.yaml"
    before = yaml.safe_load(source.read_text("utf-8")) if source.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / PEM).write_bytes(pem)
    record = {
        "name": "C2PA Trust List",
        "url": f"https://github.com/{REPO}/tree/{commit}/trust-list",
        "commit": commit,
        "license": "CC-BY-4.0",
        "issued": info["ListIssueDateTime"],
        "next_update": info["NextUpdate"],
        "sequence": info["LoTESequenceNumber"],
        "certificates": pem.count(b"BEGIN CERTIFICATE"),
        "sha256": hashlib.sha256(pem).hexdigest(),
        "organisations": organisations,
    }
    header = (
        "# Origin of the embedded C2PA trust list. Written by\n"
        "# scripts/update_c2pa_trust.py; the sha256 is checked at load.\n"
    )
    dumped = yaml.safe_dump(record, sort_keys=False, allow_unicode=True)
    source.write_text(header + dumped, encoding="utf-8")

    old = set(before.get("organisations", []))
    print(f"C2PA trust list issued {record['issued']}, {record['certificates']} certs")
    for name in sorted(set(organisations) - old):
        print(f"  + {name}")
    for name in sorted(old - set(organisations)):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
