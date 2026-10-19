#!/usr/bin/env python3
"""The research engine routes a goal and writes the nine-step artifacts offline."""

import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "guest/package/spikers-science-pal-research"
LIB = PKG / "files/usr/lib/spikers-science-pal-research"
JUDGES = PKG / "files/usr/share/spikers-science-pal-research/judges.json"
sys.path.insert(0, str(LIB))

from engine.keys import path as keys_path, save
from engine.pipeline import run_pipeline
from engine.router import load_judges, route


OER = "从公开计算材料数据库出发，数据驱动地筛选低成本、高活性的替代 OER 催化剂"


class Engine(unittest.TestCase):
    def test_oer_goal_routes_to_electrocatalysis(self):
        decision = route(OER, load_judges(JUDGES))
        self.assertTrue(decision["known"])
        self.assertEqual(decision["id"], "05-wang-zhenbin")

    def test_unknown_goal_stays_unknown(self):
        decision = route("给温室番茄设计滴灌排班", load_judges(JUDGES))
        self.assertFalse(decision["known"])

    def test_another_field_uses_the_same_steps_without_catalysis_wording(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            context = run_pipeline("把一段语音按能量切开", JUDGES, home / "science", offline=True)
            self.assertEqual(context["decision"]["id"], "06-wang-li")
            text = context["report"].read_text(encoding="utf-8")
            self.assertNotIn("吸附能", text)
            self.assertNotIn("Catalysis-Hub", text)
            self.assertIn("离线回退，非作品结论", text)
            self.assertTrue((context["directory"] / "workspace" / "top10.csv").is_file())
        decision = route("给温室番茄设计滴灌排班", load_judges(JUDGES))
        self.assertFalse(decision["known"])

    def test_offline_oer_run_writes_report_and_top10(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            context = run_pipeline(OER, JUDGES, home / "science", offline=True, stamp="test")
            report = context["report"]
            self.assertTrue(report.is_file())
            text = report.read_text(encoding="utf-8")
            self.assertIn("离线回退，非作品结论", text)
            self.assertIn("等宽区间不改域内均值排序", text)
            top10 = context["directory"] / "workspace" / "top10.csv"
            self.assertGreaterEqual(len(top10.read_text(encoding="utf-8").splitlines()), 11)
            self.assertTrue((context["export"] / "report.html").is_file())
            self.assertTrue(any(line.startswith("[3/9]") for line in context["logs"]))
            self.assertTrue(any(line.startswith("[9/9]") for line in context["logs"]))

    def test_unknown_goal_scaffolds_and_still_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            context = run_pipeline("给温室番茄设计滴灌排班", JUDGES, home / "science", offline=True)
            self.assertFalse(context["decision"]["known"])
            self.assertTrue((context["directory"] / "platform-handoff.md").is_file())
            self.assertTrue((context["directory"] / "descriptors.md").is_file())
            self.assertTrue(context["report"].is_file())

    def test_api_key_file_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            os.environ["HOME"] = str(home)
            os.environ["XDG_CONFIG_HOME"] = str(home / ".config")
            written = save({"materials_project": "not-a-real-key"})
            self.assertEqual(written, keys_path())
            self.assertEqual(stat.S_IMODE(written.stat().st_mode), 0o600)
            self.assertNotIn("not-a-real-key", JUDGES.read_text(encoding="utf-8"))

    def test_cli_offline_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "SCIENCE_ROOT": str(home / "science"),
                "SPIKERS_SCIENCE_PAL_JUDGES_DATA": str(JUDGES),
                "SPIKERS_SCIENCE_PAL_ENGINE_FOREGROUND": "1",
                "SPIKERS_SCIENCE_PAL_ENGINE_OFFLINE": "1",
            })
            result = subprocess.run(
                [sys.executable, str(LIB / "engine" / "main.py"), "--goal", OER, "--offline", "--inside"],
                env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("05-wang-zhenbin", result.stdout)
            self.assertTrue((home / "science" / "domains" / "05-wang-zhenbin" / "workspace" / "report.html").is_file())

    def test_agent_prompt_calls_both_apps(self):
        from engine.session import task_prompt
        text = task_prompt("统计一段语音里的停顿")
        self.assertIn("spikers-science-pal-engine --execute --goal", text)
        self.assertIn("spikers-science-pal-sciencepal", text)
        self.assertIn("统计一段语音里的停顿", text)
        self.assertNotIn("吸附能", text)

    def test_skill_link_is_created(self):
        skill = PKG / "files/usr/share/spikers-science-pal-research/skills/spikers-research"
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "SPIKERS_SCIENCE_PAL_SKILL_DIR": str(skill),
            })
            result = subprocess.run(
                [sys.executable, str(LIB / "engine" / "install_skill.py")],
                env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            link = home / ".config/opencode/skills/spikers-research"
            self.assertTrue(link.is_symlink())
            self.assertTrue((link / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
