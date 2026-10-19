#!/usr/bin/env python3
"""The platform bridge talks to a local stand-in of sciencepal.ai."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "guest/package/spikers-science-pal-research/files/usr/lib/spikers-science-pal-research"
sys.path.insert(0, str(LIB))

from engine.bridge import capture_login, save_token, token_path
from engine.handoff import complete_goal
from engine.newdomain import draft


JUDGES = ROOT / "guest/package/spikers-science-pal-research/files/usr/share/spikers-science-pal-research/judges.json"
METHOD = json.dumps({
    "domain": "设施园艺",
    "data_sources": ["https://example.test/tomato"],
    "features": ["水分（土壤）", "光照"],
    "model": "岭回归，留一",
    "screening": "按产量排序",
    "verification": "需田间试验",
}, ensure_ascii=False)


class Platform(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/agents"):
            self._json({"agents": [
                {"agent_id": "lit", "name": "Spiker's Literature Discovery Lab"},
                {"agent_id": "cat", "name": "Spiker's Electrocat Lab"},
            ]})
            return
        if self.path.startswith("/api/thread/") and self.path.endswith("/agent-runs"):
            self._json({"agent_runs": [{"agent_run_id": "run-1", "status": "completed"}]})
            return
        if self.path.startswith("/rest/v1/messages"):
            content = METHOD if "method" in getattr(self.server, "mode", "") else "平台已按虚拟机报告写完。"
            self._json([{
                "type": "assistant",
                "created_at": "2026-10-19T00:00:00Z",
                "content": json.dumps({"role": "assistant", "content": content}),
            }])
            return
        self._json({"detail": "missing"}, status=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.path.startswith("/api/agent/initiate"):
            self._json({"thread_id": "thread-1", "agent_run_id": "run-1", "project_id": "project-1"})
            return
        if self.path.startswith("/api/workspace/files/upload"):
            self._json({"uploaded": ["file"]})
            return
        self._json({"detail": "missing"}, status=404)

    def _json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


class BridgeTests(unittest.TestCase):
    def test_login_capture_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            profile = home / "browser/Default/Local Storage/leveldb"
            profile.mkdir(parents=True)
            (profile / "000001.log").write_text(
                'noise "access_token":"eyJheader.payload.sig" "refresh_token":"refresh-1" "expires_at": 2000000000 ',
                encoding="utf-8")
            os.environ["HOME"] = str(home)
            os.environ["XDG_CONFIG_HOME"] = str(home / ".config")
            os.environ["SPIKERS_SCIENCE_PAL_BROWSER_PROFILE"] = str(home / "browser")
            capture_login()
            saved = token_path()
            self.assertEqual(stat.S_IMODE(saved.stat().st_mode), 0o600)
            self.assertIn("eyJheader.payload.sig", saved.read_text(encoding="utf-8"))

    def test_new_goal_uses_platform_method_without_a_paste(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
            server.mode = "method"
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            os.environ.update({
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "SCIENCE_ROOT": str(home / "science"),
                "SPIKERS_SCIENCE_PAL_BACKEND_URL": "http://127.0.0.1:{}/api".format(port),
                "SPIKERS_SCIENCE_PAL_SUPABASE_URL": "http://127.0.0.1:{}".format(port),
                "SPIKERS_SCIENCE_PAL_BRIDGE_PAUSE": "0",
                "SPIKERS_SCIENCE_PAL_BRIDGE_POLLS": "3",
            })
            save_token({"access_token": "good", "refresh_token": "refresh-1", "expires_at": 2000000000})
            try:
                context = complete_goal(
                    "给温室番茄设计滴灌排班", JUDGES, home / "science",
                    False, False, lambda goal, decision: draft(goal, decision))
            finally:
                server.shutdown()
                server.server_close()
            self.assertTrue(any("方法学已取回" in line for line in context["logs"]))
            self.assertIn("按产量排序", context["report"].read_text(encoding="utf-8"))

    def test_known_goal_asks_the_field_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
            server.mode = "deepen"
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            os.environ.update({
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "SPIKERS_SCIENCE_PAL_BACKEND_URL": "http://127.0.0.1:{}/api".format(port),
                "SPIKERS_SCIENCE_PAL_SUPABASE_URL": "http://127.0.0.1:{}".format(port),
                "SPIKERS_SCIENCE_PAL_BRIDGE_PAUSE": "0",
                "SPIKERS_SCIENCE_PAL_BRIDGE_POLLS": "3",
            })
            save_token({"access_token": "good", "refresh_token": "refresh-1", "expires_at": 2000000000})
            try:
                context = complete_goal(
                    "筛选低成本高活性的替代 OER 催化剂", JUDGES, home / "science",
                    False, False, lambda goal, decision: None)
            finally:
                server.shutdown()
                server.server_close()
            self.assertTrue((context["export"] / "platform.md").is_file())
            self.assertIn("平台已按虚拟机报告写完", (context["export"] / "platform.md").read_text(encoding="utf-8"))
            self.assertTrue(any("Agent 深化完成" in line for line in context["logs"]))

    def test_cli_login(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            profile = home / "browser/Default/Local Storage/leveldb"
            profile.mkdir(parents=True)
            (profile / "000001.log").write_text(
                '"access_token":"eyJabc.def.ghi" "refresh_token":"refresh-9" "expires_at": 2000000000',
                encoding="utf-8")
            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "SPIKERS_SCIENCE_PAL_BROWSER_PROFILE": str(home / "browser"),
            })
            result = subprocess.run(
                [sys.executable, str(LIB / "engine" / "bridge.py"), "login"],
                env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("0600", result.stdout)


if __name__ == "__main__":
    unittest.main()
