#!/usr/bin/env python3
"""The Mac click installer updates an app's factory and leaves an existing VM disk alone."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/mac-click-install-research-vm.sh"


def write_executable(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class MacClickInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="mac-click-installer-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.fixture = self.root / "fixture"
        self.fixture.mkdir()
        self.image = b"factory-image-0.4.8"
        (self.fixture / "image.zst").write_bytes(self.image)
        self.compressed_sha = hashlib.sha256(self.image).hexdigest()
        self.disk_sha = "b" * 64
        write_executable(self.bin / "plutil", textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json, sys
            from pathlib import Path

            args = sys.argv[1:]
            if args[0] == "-extract":
                key, raw, dash_o, dash = args[1:5]
                assert raw == "raw" and dash_o == "-o" and dash == "-"
                path = Path(args[5])
                value = json.loads(path.read_text())
                for part in key.split("."):
                    value = value[part]
                print(value)
            elif args[0] == "-replace":
                key, kind, value, path = args[1], args[2], args[3], Path(args[4])
                payload = json.loads(path.read_text())
                cursor = payload
                parts = key.split(".")
                for part in parts[:-1]:
                    cursor = cursor[part]
                if kind == "-integer":
                    cursor[parts[-1]] = int(value)
                elif kind == "-string":
                    cursor[parts[-1]] = value
                else:
                    raise SystemExit("unsupported plutil type")
                path.write_text(json.dumps(payload) + "\\n")
            else:
                raise SystemExit("unsupported plutil command")
            """
        ))
        write_executable(self.bin / "osascript", textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import sys
            script = sys.stdin.read()
            if "开始安装" in script:
                print("开始安装")
            """
        ))
        write_executable(self.bin / "codesign", textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import pathlib, sys
            app = pathlib.Path(sys.argv[-1])
            (app / "codesign-args").write_text("\\n".join(sys.argv))
            if pathlib.Path(app.parent.parent / "codesign-fail").exists():
                raise SystemExit(1)
            """
        ))

    def environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update({
            "HOME": str(self.home),
            "SPIKERS_INSTALLER_TEST": "1",
            "SPIKERS_PLUTIL": str(self.bin / "plutil"),
            "SPIKERS_OSASCRIPT": str(self.bin / "osascript"),
            "SPIKERS_CODESIGN": str(self.bin / "codesign"),
            "SPIKERS_INSTALLER_FIXTURE_DIR": str(self.fixture),
            "SPIKERS_INSTALLER_DISK_SHA": self.disk_sha,
            "SPIKERS_INSTALLER_COMPRESSED_SHA": self.compressed_sha,
            "SPIKERS_INSTALLER_COMPRESSED_BYTES": str(len(self.image)),
            "PATH": f"{self.bin}:/usr/bin:/bin",
        })
        return environment

    def run_installer(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(INSTALLER)],
            check=False, capture_output=True, text=True, env=self.environment(),
        )

    def make_app(self, name: str) -> Path:
        app = self.home / "Applications" / name
        guest = app / "Contents/Resources/guest"
        guest.mkdir(parents=True)
        (guest / "factory.json").write_text(json.dumps({
            "format": 1,
            "kind": "upstream-shell-factory",
            "boot": "uefi-limine",
            "compressed": {"path": "spikers-aarch64-edge.img.zst", "sha256": "a" * 64},
            "disk": {"path": "spikers-aarch64-edge.img", "bytes": 10, "sha256": "c" * 64},
        }) + "\n")
        (guest / "packages.txt").write_text("kept\n")
        (guest / "SHA256SUMS").write_text(
            f"{'d' * 64}  spikers-aarch64-edge.img.zst\n"
            f"{'e' * 64}  factory.json\n"
            f"{'f' * 64}  packages.txt\n"
        )
        (guest / "spikers-aarch64-edge.img.zst").write_bytes(b"old-image")
        return app

    def existing_disk(self) -> Path:
        disk = (self.home / "Library/Application Support/Spiker's Science Pal"
                / "VM/v1/shell/disk.img")
        disk.parent.mkdir(parents=True)
        disk.write_bytes(b"KEEP")
        (disk.parent.parent / "shell-factory").mkdir()
        return disk

    def test_manifest_lists_four_parts_that_sum_to_the_image(self) -> None:
        result = subprocess.run(
            ["bash", str(INSTALLER), "--print-manifest"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        manifest = json.loads(result.stdout)
        self.assertEqual("0.4.8", manifest["version"])
        self.assertEqual(manifest["compressed_bytes"], sum(part["bytes"] for part in manifest["parts"]))
        self.assertEqual(4, len(manifest["parts"]))
        self.assertEqual(64, len(manifest["disk_sha256"]))
        self.assertEqual(64, len(manifest["compressed_sha256"]))
        self.assertIn("factory-2026-10-19-research-0.4.8", manifest["base_url"])
        for part in manifest["parts"]:
            self.assertEqual(64, len(part["sha256"]))
            self.assertTrue(part["name"].startswith("spikers-aarch64-edge.img.zst."))

    def test_install_replaces_the_bundled_factory_and_keeps_the_vm_disk(self) -> None:
        app = self.make_app("Spiker's Science Pal.app")
        dev = self.make_app("Spiker's Science Pal Dev.app")
        disk = self.existing_disk()
        result = self.run_installer()
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("ALERT", result.stdout)
        self.assertIn("0.4.8", result.stdout)
        self.assertEqual(b"KEEP", disk.read_bytes())
        for installed in (app, dev):
            guest = installed / "Contents/Resources/guest"
            factory = json.loads((guest / "factory.json").read_text())
            self.assertEqual(self.disk_sha, factory["disk"]["sha256"])
            self.assertEqual(self.compressed_sha, factory["compressed"]["sha256"])
            self.assertEqual(21474836480, factory["disk"]["bytes"])
            self.assertEqual(self.image, (guest / "spikers-aarch64-edge.img.zst").read_bytes())
            download = json.loads((guest / "download.json").read_text())
            self.assertEqual(self.disk_sha, download["identity"])
            self.assertEqual(self.compressed_sha, download["image"]["sha256"])
            self.assertIn("--preserve-metadata=identifier,entitlements,flags,runtime",
                          (installed / "codesign-args").read_text())
            sums = (guest / "SHA256SUMS").read_text()
            self.assertIn(f"{self.compressed_sha}  spikers-aarch64-edge.img.zst", sums)
            self.assertIn(f"{'f' * 64}  packages.txt", sums)
        cached = (disk.parent.parent / "shell-factory" / f"{self.disk_sha}.img.zst")
        self.assertEqual(self.image, cached.read_bytes())
        self.assertIn("旧磁盘", result.stdout)

    def test_without_an_app_saves_the_disk_on_the_desktop(self) -> None:
        result = self.run_installer()
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        saved = self.home / "Desktop/SpikersSciencePal-vm/spikers-aarch64-edge.img.zst"
        self.assertEqual(self.image, saved.read_bytes())
        self.assertIn("0.4.8", (self.home / "Desktop/SpikersSciencePal-vm/说明.txt").read_text())
        self.assertIn("Mac App", result.stdout)
        self.assertFalse((self.home / "Desktop/Spiker's Science Pal.app").exists())

    def test_a_bad_download_does_not_change_the_app_or_the_vm_disk(self) -> None:
        app = self.make_app("Spiker's Science Pal.app")
        disk = self.existing_disk()
        environment = self.environment()
        environment["SPIKERS_INSTALLER_COMPRESSED_SHA"] = "9" * 64
        result = subprocess.run(
            ["bash", str(INSTALLER)],
            check=False, capture_output=True, text=True, env=environment,
        )
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("没有通过校验", result.stdout)
        guest = app / "Contents/Resources/guest"
        factory = json.loads((guest / "factory.json").read_text())
        self.assertEqual("c" * 64, factory["disk"]["sha256"])
        self.assertEqual(b"old-image", (guest / "spikers-aarch64-edge.img.zst").read_bytes())
        self.assertEqual(b"KEEP", disk.read_bytes())
        self.assertFalse((guest / "download.json").exists())

    def test_a_failed_signature_rolls_the_app_back(self) -> None:
        app = self.make_app("Spiker's Science Pal.app")
        (self.home / "codesign-fail").write_text("1\n")
        result = self.run_installer()
        self.assertEqual(1, result.returncode, result.stderr + result.stdout)
        guest = app / "Contents/Resources/guest"
        factory = json.loads((guest / "factory.json").read_text())
        self.assertEqual("c" * 64, factory["disk"]["sha256"])
        self.assertEqual(b"old-image", (guest / "spikers-aarch64-edge.img.zst").read_bytes())
        self.assertFalse((guest / "download.json").exists())
        self.assertIn("没有装上", result.stdout)


if __name__ == "__main__":
    unittest.main()
