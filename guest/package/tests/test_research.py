#!/usr/bin/env python3
"""Offline contracts for the research workbench: 45 scripts, fetch skip, menu, matrix."""

import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "guest/package/spikers-science-pal-research"
JUDGES = PKG / "files/usr/share/spikers-science-pal-research/judges.json"
BUILD = PKG / "tools/build-judges.py"
LIB = PKG / "files/usr/lib/spikers-science-pal-research"
BIN = PKG / "files/usr/bin"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ResearchPackage(unittest.TestCase):
    def test_judges_json_matches_the_generator(self):
        generated = subprocess.check_output(["python3", str(BUILD)])
        self.assertEqual(generated, JUDGES.read_bytes())

    def test_forty_five_scripts_and_fetch_scripts(self):
        data = json.loads(JUDGES.read_text())
        self.assertEqual(len(data["judges"]), 15)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for judge in data["judges"]:
                work = root / judge["id"]
                work.mkdir()
                levels = {
                    "launchpad": judge["capabilities"]["workflow"]["code"],
                    "l2": judge["capabilities"]["deep"]["l2"]["code"],
                    "l3": judge["capabilities"]["deep"]["l3"]["code"],
                }
                for name, code in levels.items():
                    (work / (name + ".py")).write_text(code)
                    result = subprocess.run(
                        ["python3", name + ".py"], cwd=work, capture_output=True, text=True, timeout=120)
                    self.assertEqual(result.returncode, 0, (judge["id"], name, result.stderr[-400:]))
                l3 = judge["capabilities"]["deep"]["l3"]
                fetch = l3["data_fetch"]
                self.assertTrue(fetch.startswith("#!/bin/bash"), judge["id"])
                self.assertIn("数据已就绪，使用本地数据", fetch)
                self.assertIn("SOURCE.txt", fetch)
                if judge["id"] not in {"09-wang-maolin", "14-liu-jiayu"}:
                    self.assertIn("合成数据冒烟，非作品结论", l3["code"])
                script = work / "data" / "data_fetch.sh"
                script.parent.mkdir(exist_ok=True)
                script.write_text(fetch)
                script.chmod(0o755)
                checked = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                match = re.search(r"^mkdir -p (raw/\S+)", fetch, re.M)
                self.assertIsNotNone(match, judge["id"])
                seeded = work / "data" / match.group(1)
                seeded.mkdir(parents=True)
                (seeded / "payload.bin").write_bytes(b"already")
                first = subprocess.run(["bash", str(script)], cwd=work, capture_output=True, text=True, timeout=20)
                second = subprocess.run(["bash", str(script)], cwd=work, capture_output=True, text=True, timeout=20)
                self.assertEqual(first.returncode, 0, (judge["id"], first.stderr, first.stdout))
                self.assertEqual(second.returncode, 0, (judge["id"], second.stderr))
                self.assertIn("数据已就绪，使用本地数据", first.stdout)
                self.assertIn("数据已就绪，使用本地数据", second.stdout)
                report = work / "workspace" / "report.html"
                self.assertTrue(report.is_file(), judge["id"])

    def test_menu_injection_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            menu = home / "menu-default.jsonc"
            menu.write_text('{\n  "setup.example": {"label":"Example","action":"true"},\n}\n')
            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_STATE_HOME": str(home / ".local/state"),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "SPIKERS_SCIENCE_PAL_JUDGES_DATA": str(JUDGES),
                "SPIKERS_SCIENCE_PAL_SPIKERS_MENU": str(menu),
            })
            script = LIB / "menu-entries"
            for _ in range(2):
                result = subprocess.run(["python3", str(script)], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            text = (home / ".config/omarchy/extensions/omarchy-menu.jsonc").read_text()
            data = json.loads(subprocess.check_output(
                ["python3", "-c",
                 "import json,re,sys; t=sys.stdin.read(); t=re.sub(r'^\\s*//[^\\n]*(\\n|$)','',t,flags=re.M); "
                 "print(json.dumps(json.loads(re.sub(r',(\\s*[}\\]])', r'\\1', t))))"],
                input=text, text=True))
            keys = [key for key in data if key == "research" or key.startswith("research.")]
            self.assertEqual(len(keys), 22, keys)
            self.assertNotIn("action", data["research"])
            self.assertEqual(data["research"]["label"], "科研")
            self.assertEqual(data["research.05-wang-zhenbin"]["label"], "电催化")
            self.assertIn("spikers-science-pal-research-app 05-wang-zhenbin",
                          data["research.05-wang-zhenbin"]["action"])
            self.assertEqual(data["research.overview"]["action"], "spikers-science-pal-domain overview")
            self.assertEqual(data["engine"]["label"], "Spiker 科研引擎")
            self.assertEqual(data["engine"]["action"], "spikers-science-pal-engine")
            self.assertIn("sciencepal.ai", data["sciencepal"]["description"])
            self.assertLess(text.find('"engine"'), text.find('"research"'))
            self.assertLess(text.find('"sciencepal"'), text.find('"research"'))
            before = text
            subprocess.run(["python3", str(script)], env=env, check=True)
            self.assertEqual(before, (home / ".config/omarchy/extensions/omarchy-menu.jsonc").read_text())

    def test_capability_matrix_serves_sixteen_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            port = str(free_port())
            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "SPIKERS_SCIENCE_PAL_JUDGES_DATA": str(JUDGES),
                "SPIKERS_SCIENCE_PAL_SHOWCASE_PORT": port,
            })
            generated = subprocess.run(["python3", str(LIB / "generate-showcase")], env=env, capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            pages = list((home / ".local/share/spikers-science-pal-research/showcase").rglob("*.html"))
            self.assertEqual(len(pages), 16)
            server = subprocess.Popen(
                ["bash", str(BIN / "spikers-science-pal-showcase-server")],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                body = b""
                for _ in range(40):
                    try:
                        with urllib.request.urlopen("http://127.0.0.1:{}/".format(port), timeout=1) as response:
                            body = response.read()
                        break
                    except OSError:
                        time.sleep(0.1)
                self.assertIn("科研功能矩阵".encode(), body)
                with urllib.request.urlopen("http://127.0.0.1:{}/judges/05-wang-zhenbin/".format(port), timeout=2) as response:
                    page = response.read()
                self.assertIn("data_fetch".encode(), page)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    server.kill()

    def test_domain_workbench_writes_executable_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "domain"
            env = os.environ.copy()
            env["SPIKERS_SCIENCE_PAL_JUDGES_DATA"] = str(JUDGES)
            result = subprocess.run(
                ["python3", str(LIB / "domain-workbench"), "05-wang-zhenbin", str(target)],
                env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            fetch = target / "data" / "data_fetch.sh"
            self.assertTrue(fetch.stat().st_mode & 0o111)
            self.assertTrue((target / "l3_extend.py").is_file())
            self.assertTrue((target / "l3_extend.ipynb").is_file())
            shutil.rmtree(target)

    def test_old_flat_menu_rows_become_the_research_column(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            old = ('  "judges.05-wang-zhenbin": {"icon":"x","label":"old",'
                   '"action":"spikers-science-pal-domain 05-wang-zhenbin"},\n')
            extension = home / ".config/omarchy/extensions"
            extension.mkdir(parents=True)
            (extension / "omarchy-menu.jsonc").write_text("{\n" + old + "}\n")
            state = home / ".local/state/spikers-science-pal-research"
            state.mkdir(parents=True)
            (state / "menu-entries").write_text("1\n")
            (state / "menu-rows.json").write_text(json.dumps(
                {"judges.05-wang-zhenbin": old}, ensure_ascii=False))
            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_STATE_HOME": str(home / ".local/state"),
                "SPIKERS_SCIENCE_PAL_JUDGES_DATA": str(JUDGES),
                "SPIKERS_SCIENCE_PAL_SPIKERS_MENU": str(home / "menu-default.jsonc"),
            })
            (home / "menu-default.jsonc").write_text("{}\n")
            result = subprocess.run(
                ["python3", str(LIB / "menu-entries")], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (extension / "omarchy-menu.jsonc").read_text()
            self.assertNotIn("judges.05-wang-zhenbin", text)
            self.assertIn('"research":', text)
            self.assertIn("电催化", text)

    def test_field_app_runs_the_practice_script(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "SCIENCE_ROOT": str(home / "science"),
                "SPIKERS_SCIENCE_PAL_JUDGES_DATA": str(JUDGES),
                "SPIKERS_SCIENCE_PAL_DOMAIN_WORKBENCH": str(LIB / "domain-workbench"),
                "SPIKERS_SCIENCE_PAL_RESEARCH_INIT": str(BIN / "spikers-science-pal-research-init"),
                "SPIKERS_SCIENCE_PAL_RESEARCH_FOREGROUND": "1",
            })
            result = subprocess.run(
                ["python3", str(LIB / "research-app"), "--inside", "05-wang-zhenbin"],
                env=env, input="1\n\nq\n", capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("电催化", result.stdout)
            self.assertIn("开箱演示", result.stdout)
            self.assertIn("预测活性", result.stdout)
            self.assertNotIn("退出码", result.stdout)

    def test_desktop_entries_list_each_field(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "SPIKERS_SCIENCE_PAL_JUDGES_DATA": str(JUDGES),
            })
            script = LIB / "desktop-entries"
            for _ in range(2):
                result = subprocess.run(["python3", str(script)], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            apps = home / ".local/share/applications"
            catalysis = (apps / "spikers-science-pal-research-05-wang-zhenbin.desktop").read_text()
            self.assertIn("Name=科研 · 电催化", catalysis)
            self.assertIn("Exec=spikers-science-pal-research-app 05-wang-zhenbin", catalysis)
            self.assertIn("Terminal=false", catalysis)
            self.assertEqual(len(list(apps.glob("spikers-science-pal-research-*.desktop"))), 18)
            stale = apps / "spikers-science-pal-research-99-gone.desktop"
            stale.write_text("[Desktop Entry]\nX-Spikers-Science-Pal-Research=99-gone\n")
            subprocess.run(["python3", str(script)], env=env, check=True)
            self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
