#!/usr/bin/env python3
"""Assemble dist/guest from the published 0.4.8 factory, without the 20 GiB disk.

The Mac app build only needs the manifest, the package list, and the
integration package. The compressed disk stays on the GitHub release and the
app downloads it the first time it creates a VM.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import urllib.request

from factory_download import INTEGRATION_PACKAGE, RESEARCH_VERSION, assemble


SOURCE_RELEASE = "https://github.com/tspike630/Spiker-s-science-pal/releases/download/factory-2026-10-19"
PUBLISHED_RELEASE = (
    "https://github.com/tspike630/Spiker-s-science-pal/releases/download/"
    "factory-2026-10-19-research-0.4.8"
)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "spikers-science-pal-prepare"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if len(data) > 2_000_000:
        raise ValueError(f"{url} is unexpectedly large")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    factory = json.loads(fetch(f"{SOURCE_RELEASE}/factory.json"))
    packages = fetch(f"{SOURCE_RELEASE}/packages.txt").decode()
    manifest = json.loads(fetch(f"{PUBLISHED_RELEASE}/download.json"))
    package = args.root / "guest" / "prebuilt" / INTEGRATION_PACKAGE
    assemble(args.output, factory, packages, manifest, package)
    print(f"[guest] prepared {args.output} for research {RESEARCH_VERSION}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"prepare-published-guest: {error}", file=sys.stderr)
        raise SystemExit(1)
