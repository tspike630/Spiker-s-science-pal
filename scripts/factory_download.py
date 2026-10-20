#!/usr/bin/env python3
"""Check the factory download manifest the Mac app fetches on first launch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys


DIGEST = re.compile(r"[0-9a-f]{64}")
DISK_SHA256 = "33caf5836b86a86aba300b2ea1242515f8b7ec406dfd3c55cc18cafd75a0992e"
COMPRESSED_SHA256 = "9f9a4b474e05f1bf8ccef8de7222c647eae844eab485cc5f0acdab530222383e"
COMPRESSED_NAME = "spikers-aarch64-edge.img.zst"
DISK_BYTES = 21474836480
RESEARCH_VERSION = "0.4.8-1"
RESEARCH_LINE = re.compile(r"^spikers-science-pal-research \S+$", re.MULTILINE)
INTEGRATION_PACKAGE = "spikers-science-pal-0.1.0-23-aarch64.pkg.tar.zst"
SUMMED = ("factory.json", "packages.txt", "unavailable.txt", "download.json")


def update_factory(factory: dict, disk_sha: str, compressed_sha: str) -> dict:
    """Return a factory manifest whose disk identity is the published 0.4.8 image."""
    if not DIGEST.fullmatch(disk_sha) or not DIGEST.fullmatch(compressed_sha):
        raise ValueError("replacement digests are invalid")
    updated = json.loads(json.dumps(factory))
    if updated.get("kind") != "upstream-shell-factory" or updated.get("format") != 1:
        raise ValueError("unsupported factory")
    if updated.get("boot") != "uefi-limine":
        raise ValueError("the factory does not boot through UEFI")
    if updated["compressed"]["path"] != COMPRESSED_NAME:
        raise ValueError("unexpected compressed factory name")
    if updated["disk"]["bytes"] != DISK_BYTES:
        raise ValueError("unexpected factory disk size")
    updated["disk"]["sha256"] = disk_sha
    updated["compressed"]["sha256"] = compressed_sha
    return updated


def replace_research_version(packages: str, version: str) -> str:
    """Point the one research row in packages.txt at the version installed in the disk."""
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+-[0-9]+", version):
        raise ValueError("research version is invalid")
    if len(RESEARCH_LINE.findall(packages)) != 1:
        raise ValueError("packages.txt must name the research package once")
    return RESEARCH_LINE.sub(f"spikers-science-pal-research {version}", packages, count=1)


def check_manifest(factory: dict, manifest: dict) -> None:
    """Reject a download manifest that does not describe this factory disk."""
    disk = factory["disk"]["sha256"]
    compressed = factory["compressed"]["sha256"]
    if not DIGEST.fullmatch(str(disk)) or not DIGEST.fullmatch(str(compressed)):
        raise ValueError("factory digests are invalid")
    if manifest.get("format") != 1 or manifest.get("kind") != "spikers-science-pal-factory-download":
        raise ValueError("unsupported download manifest")
    if manifest.get("identity") != disk:
        raise ValueError("download identity does not match the factory disk")
    image = manifest["image"]
    if image.get("sha256") != compressed:
        raise ValueError("download image does not match the compressed factory")
    size = image.get("bytes")
    if not isinstance(size, int) or size <= 0:
        raise ValueError("download image size is invalid")
    parts = manifest.get("parts")
    if not isinstance(parts, list) or not parts or len(parts) > 64:
        raise ValueError("download manifest has no usable parts")
    total = 0
    for part in parts:
        url = part.get("url")
        if not isinstance(url, str) or not url.startswith("https://") or any(
            character in url for character in " \n\r"
        ):
            raise ValueError("download part URL is invalid")
        digest = part.get("sha256")
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise ValueError("download part digest is invalid")
        part_size = part.get("bytes")
        if not isinstance(part_size, int) or part_size <= 0:
            raise ValueError("download part size is invalid")
        total += part_size
    if total != size:
        raise ValueError("download parts do not add up to the image")


def write_sums(directory: Path) -> None:
    lines = []
    for name in SUMMED:
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}\n")
    (directory / "SHA256SUMS").write_text("".join(lines))


def assemble(
    output: Path,
    factory: dict,
    packages: str,
    manifest: dict,
    package: Path,
) -> None:
    updated = update_factory(factory, DISK_SHA256, COMPRESSED_SHA256)
    packages_text = replace_research_version(packages, RESEARCH_VERSION)
    check_manifest(updated, manifest)
    if not package.is_file() or package.is_symlink() or package.name != INTEGRATION_PACKAGE:
        raise ValueError(f"integration package is missing or unsafe: {package}")
    output.mkdir(parents=True, exist_ok=True)
    packages_dir = output / "packages"
    packages_dir.mkdir(exist_ok=True)
    for child in packages_dir.iterdir():
        if child.is_symlink() or not child.is_file():
            raise ValueError(f"guest package directory has an unexpected entry: {child.name}")
        child.unlink()
    (output / "factory.json").write_text(json.dumps(updated, indent=2) + "\n")
    (output / "packages.txt").write_text(packages_text)
    (output / "unavailable.txt").write_text("")
    (output / "download.json").write_text(json.dumps(manifest, indent=2) + "\n")
    write_sums(output)
    shutil.copyfile(package, packages_dir / INTEGRATION_PACKAGE)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check",))
    parser.add_argument("--factory", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    factory = json.loads(args.factory.read_text())
    manifest = json.loads(args.manifest.read_text())
    check_manifest(factory, manifest)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"factory-download: {error}", file=sys.stderr)
        raise SystemExit(1)
