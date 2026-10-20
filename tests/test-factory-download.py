#!/usr/bin/env python3
"""The published 0.4.8 manifest stays tied to the factory the Mac app boots."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import factory_download


class FactoryDownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="factory-download-")
        self.addCleanup(self.temporary.cleanup)
        self.factory = {
            "format": 1,
            "kind": "upstream-shell-factory",
            "boot": "uefi-limine",
            "disk": {
                "path": "spikers-aarch64-edge.img",
                "bytes": factory_download.DISK_BYTES,
                "sha256": "a" * 64,
            },
            "compressed": {
                "path": factory_download.COMPRESSED_NAME,
                "sha256": "b" * 64,
            },
        }
        self.manifest = {
            "format": 1,
            "kind": "spikers-science-pal-factory-download",
            "identity": factory_download.DISK_SHA256,
            "image": {"bytes": 3, "sha256": factory_download.COMPRESSED_SHA256},
            "parts": [
                {
                    "url": "https://example.invalid/disk.001",
                    "bytes": 2,
                    "sha256": "c" * 64,
                },
                {
                    "url": "https://example.invalid/disk.002",
                    "bytes": 1,
                    "sha256": "d" * 64,
                },
            ],
        }

    def test_update_replaces_only_the_digests(self) -> None:
        updated = factory_download.update_factory(
            self.factory,
            factory_download.DISK_SHA256,
            factory_download.COMPRESSED_SHA256,
        )
        self.assertEqual(factory_download.DISK_SHA256, updated["disk"]["sha256"])
        self.assertEqual(factory_download.COMPRESSED_SHA256, updated["compressed"]["sha256"])
        self.assertEqual("a" * 64, self.factory["disk"]["sha256"])
        factory_download.check_manifest(updated, self.manifest)

    def test_manifest_must_match_the_factory_disk(self) -> None:
        updated = factory_download.update_factory(
            self.factory,
            factory_download.DISK_SHA256,
            factory_download.COMPRESSED_SHA256,
        )
        self.manifest["identity"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "identity"):
            factory_download.check_manifest(updated, self.manifest)

    def test_research_row_is_replaced_once(self) -> None:
        text = "spikers-science-pal 0.1.0-23\nspikers-science-pal-research 0.4.0-1\n"
        updated = factory_download.replace_research_version(text, "0.4.8-1")
        self.assertEqual(
            "spikers-science-pal 0.1.0-23\nspikers-science-pal-research 0.4.8-1\n",
            updated,
        )

    def test_assemble_writes_the_guest_dir_the_app_build_reads(self) -> None:
        output = Path(self.temporary.name) / "guest"
        package = Path(self.temporary.name) / factory_download.INTEGRATION_PACKAGE
        package.write_bytes(b"package")
        factory_download.assemble(
            output,
            self.factory,
            "spikers-science-pal 0.1.0-23\nspikers-science-pal-research 0.4.0-1\n",
            self.manifest,
            package,
        )
        factory = json.loads((output / "factory.json").read_text())
        manifest = json.loads((output / "download.json").read_text())
        self.assertEqual(factory_download.DISK_SHA256, factory["disk"]["sha256"])
        factory_download.check_manifest(factory, manifest)
        self.assertIn("spikers-science-pal-research 0.4.8-1\n", (output / "packages.txt").read_text())
        self.assertTrue((output / "SHA256SUMS").is_file())
        self.assertEqual(
            [factory_download.INTEGRATION_PACKAGE],
            sorted(path.name for path in (output / "packages").iterdir()),
        )
        self.assertIn("--download-manifest", (ROOT / "macos/build-app.sh").read_text())


if __name__ == "__main__":
    unittest.main()
