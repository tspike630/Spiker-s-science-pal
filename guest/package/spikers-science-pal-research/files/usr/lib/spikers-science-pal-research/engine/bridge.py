"""Call sciencepal.ai with the user's own Supabase session.

Checked on 2026-10-19 from the public site, without sending a prompt:

  NEXT_PUBLIC_BACKEND_URL = https://sciencepal.ai/api
  NEXT_PUBLIC_SUPABASE_URL = https://dwkmdejtbxsavupvhjmc.supabase.co
  GET  /api/agents                          401, the route exists
  POST /api/agent/initiate                  401, multipart field "prompt"
  GET  /api/thread/{id}/agent-runs          401, JSON field agent_runs
  POST /api/thread/{id}/agent/start         401
  POST /api/workspace/files/upload          exists, multipart field "files"

The website reads conversation text from Supabase table public.messages
filtered by thread_id. The anon key is the public NEXT_PUBLIC_SUPABASE_ANON_KEY
shipped in the site's JavaScript. The user's access token is not in this file.
"""

import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

def backend():
    return os.environ.get("SPIKERS_SCIENCE_PAL_BACKEND_URL", "https://sciencepal.ai/api").rstrip("/")


def supabase():
    return os.environ.get(
        "SPIKERS_SCIENCE_PAL_SUPABASE_URL", "https://dwkmdejtbxsavupvhjmc.supabase.co").rstrip("/")


def anon_key():
    return os.environ.get(
        "SPIKERS_SCIENCE_PAL_SUPABASE_ANON_KEY",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR3a21kZWp0YnhzYXZ1cHZoam1jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkyNzczMjgsImV4cCI6MjA2NDg1MzMyOH0.7Y3rE9J-0iJO5Q5rrwpDDmF-auQt6VIWo2HYTA0Mjpg",
    )

FIELD_AGENTS = {
    "01-ma-weiying": "Spiker's Literature Discovery Lab",
    "02-yan-jun": "Spiker's Clinical Survival Lab",
    "03-xu-kaidi": "Spiker's Multimodal Vision Lab",
    "04-miao-ning": "Spiker's Protein Sequence Lab",
    "05-wang-zhenbin": "Spiker's Electrocat Lab",
    "06-wang-li": "Spiker's Speech Signal Lab",
    "07-guo-xingyu": "Spiker's Spatiotemporal Lab",
    "08-zhang-yuying": "Spiker's Drug Discovery Lab",
    "09-wang-maolin": "Spiker's Mathematical AI Lab",
    "10-zheng-xiang": "Spiker's Network Science Lab",
    "11-chen-weiyu": "Spiker's High-Energy Physics Lab",
    "12-zhao-yinggong": "Spiker's LLM Engineering Lab",
    "13-wang-yao": "Spiker's Medical Imaging Lab",
    "14-liu-jiayu": "Spiker's Robotics Learning Lab",
    "15-liu-gang": "Spiker's Neuro Signal Lab",
}
METHOD_AGENT = "Spiker's Literature Discovery Lab"
DONE = {"completed", "complete", "stopped", "failed", "error", "success", "cancelled", "canceled", "idle"}


class BridgeError(RuntimeError):
    pass


def token_path():
    home = Path(os.environ["HOME"])
    config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    return config / "spikers-science-pal" / "sp-token.json"


def load_token():
    file = token_path()
    if not file.is_file():
        return {}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_token(data):
    file = token_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    kept = {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "expires_at": data.get("expires_at"),
    }
    file.write_text(json.dumps(kept, indent=1) + "\n", encoding="utf-8")
    os.chmod(file, 0o600)
    return file


def _profiles():
    override = os.environ.get("SPIKERS_SCIENCE_PAL_BROWSER_PROFILE")
    if override:
        return [Path(override)]
    home = Path(os.environ["HOME"])
    return [
        home / ".config/chromium",
        home / ".config/google-chrome",
        home / ".config/google-chrome-stable",
    ]


def capture_login():
    """Read the Supabase session Chromium stored after the user signed in once."""
    found = None
    for root in _profiles():
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.stat().st_size > 8_000_000:
                continue
            if "Local Storage" not in path.as_posix() and "Session Storage" not in path.as_posix():
                continue
            try:
                text = path.read_bytes().decode("utf-8", "ignore")
            except OSError:
                continue
            match = re.search(r'"access_token"\s*:\s*"(eyJ[^"]+)"', text)
            if not match:
                continue
            window = text[match.start():match.start() + 6000]
            refresh = re.search(r'"refresh_token"\s*:\s*"([^"]+)"', window)
            if not refresh:
                continue
            expires = re.search(r'"expires_at"\s*:\s*(\d+)', window)
            found = {
                "access_token": match.group(1),
                "refresh_token": refresh.group(1),
                "expires_at": int(expires.group(1)) if expires else None,
            }
    if not found:
        raise BridgeError("没有找到 SciencePal 登录。请先打开应用2并登录，再运行 sp-bridge login。")
    save_token(found)
    return found


def _request(url, method="GET", data=None, headers=None, timeout=30):
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return response.status, dict(response.headers), body
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()
    except urllib.error.URLError as error:
        raise BridgeError("平台连不上：{}".format(error.reason)) from error


def refresh(token):
    if not token.get("refresh_token"):
        raise BridgeError("登录已过期，请重新打开应用2登录。")
    payload = json.dumps({"refresh_token": token["refresh_token"]}).encode()
    status, _headers, body = _request(
        supabase() + "/auth/v1/token?grant_type=refresh_token",
        method="POST",
        data=payload,
        headers={"apikey": anon_key(), "Content-Type": "application/json"},
    )
    if status != 200:
        raise BridgeError("登录已过期，请重新打开应用2登录。")
    fresh = json.loads(body.decode())
    save_token(fresh)
    return load_token()


def _authorized(token):
    now = int(time.time())
    expires = token.get("expires_at") or 0
    if expires and expires < now + 60:
        token = refresh(token)
    return token


def _api(path, method="GET", data=None, headers=None, timeout=30):
    token = _authorized(load_token())
    if not token.get("access_token"):
        raise BridgeError("没有 SciencePal 登录。请先打开应用2并登录，再运行 sp-bridge login。")
    sent = {"Authorization": "Bearer " + token["access_token"]}
    if headers:
        sent.update(headers)
    status, _headers, body = _request(backend() + path, method=method, data=data, headers=sent, timeout=timeout)
    if status == 401:
        token = refresh(token)
        sent["Authorization"] = "Bearer " + token["access_token"]
        status, _headers, body = _request(backend() + path, method=method, data=data, headers=sent, timeout=timeout)
    if status >= 400:
        detail = body.decode("utf-8", "replace")[:300]
        raise BridgeError("平台返回 {}：{}".format(status, detail))
    if not body:
        return {}
    return json.loads(body.decode())


def _items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("agents", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def agents():
    rows = []
    for item in _items(_api("/agents")):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("title") or "").strip()
        agent_id = str(item.get("agent_id") or item.get("id") or "").strip()
        if name or agent_id:
            rows.append({"name": name, "agent_id": agent_id})
    return rows


def _find_agent(name):
    rows = agents()
    folded = name.lower()
    for row in rows:
        if row["name"].lower() == folded or folded in row["name"].lower():
            return row
    if rows:
        return rows[0]
    raise BridgeError("平台没有返回可用的 Agent。")


def _multipart(fields, files=None):
    boundary = uuid.uuid4().hex
    chunks = []
    for key, value in fields:
        chunks.append("--{}\r\nContent-Disposition: form-data; name=\"{}\"\r\n\r\n{}\r\n".format(
            boundary, key, value).encode())
    for key, filename, content in files or []:
        chunks.append("--{}\r\nContent-Disposition: form-data; name=\"{}\"; filename=\"{}\"\r\n"
                      "Content-Type: application/octet-stream\r\n\r\n".format(
                          boundary, key, filename).encode())
        chunks.append(content)
        chunks.append(b"\r\n")
    chunks.append("--{}--\r\n".format(boundary).encode())
    return b"".join(chunks), "multipart/form-data; boundary=" + boundary


def _pick(payload, key):
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
        for child in payload.values():
            found = _pick(child, key)
            if found:
                return found
    elif isinstance(payload, list):
        for child in payload:
            found = _pick(child, key)
            if found:
                return found
    return ""


def ask(agent_name, prompt):
    agent = _find_agent(agent_name)
    body, content_type = _multipart([
        ("prompt", prompt),
        ("agent_id", agent["agent_id"]),
    ])
    payload = _api("/agent/initiate", method="POST", data=body, headers={"Content-Type": content_type}, timeout=60)
    thread_id = _pick(payload, "thread_id")
    if not thread_id:
        raise BridgeError("平台没有返回对话编号。")
    return {
        "thread_id": thread_id,
        "agent_run_id": _pick(payload, "agent_run_id"),
        "project_id": _pick(payload, "project_id"),
        "agent": agent["name"],
    }


def _runs(thread_id):
    payload = _api("/thread/{}/agent-runs".format(thread_id))
    runs = payload.get("agent_runs") if isinstance(payload, dict) else None
    return runs if isinstance(runs, list) else []


def wait(thread_id, limit=None, pause=None):
    if limit is None:
        limit = int(os.environ.get("SPIKERS_SCIENCE_PAL_BRIDGE_POLLS", "40"))
    if pause is None:
        pause = float(os.environ.get("SPIKERS_SCIENCE_PAL_BRIDGE_PAUSE", "3"))
    last = ""
    for _ in range(limit):
        runs = _runs(thread_id)
        if runs:
            status = str((runs[-1] or {}).get("status") or "").lower()
            last = status
            if status in DONE:
                return status
        time.sleep(pause)
    if last:
        return last
    return "unknown"


def _message_text(content):
    if isinstance(content, dict):
        if isinstance(content.get("content"), str):
            return content["content"]
        parts = content.get("content")
        if isinstance(parts, list):
            texts = []
            for part in parts:
                if isinstance(part, str):
                    texts.append(part)
                elif isinstance(part, dict) and isinstance(part.get("text"), str):
                    texts.append(part["text"])
            return "\n".join(texts)
    if isinstance(content, str):
        try:
            return _message_text(json.loads(content))
        except ValueError:
            return content
    return ""


def pull(thread_id):
    token = _authorized(load_token())
    query = "/rest/v1/messages?thread_id=eq.{}&select=type,content,created_at&order=created_at.asc".format(thread_id)
    status, _headers, body = _request(
        supabase() + query,
        headers={"apikey": anon_key(), "Authorization": "Bearer " + token["access_token"]},
    )
    if status == 401:
        token = refresh(token)
        status, _headers, body = _request(
            supabase() + query,
            headers={"apikey": anon_key(), "Authorization": "Bearer " + token["access_token"]},
        )
    if status >= 400:
        raise BridgeError("读不到平台回复：{}".format(status))
    rows = json.loads(body.decode() or "[]")
    texts = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("type") not in {"assistant", "user"}:
            continue
        text = _message_text(row.get("content"))
        if text:
            texts.append(text)
    assistant = [row for row in rows if isinstance(row, dict) and row.get("type") == "assistant"]
    final = _message_text(assistant[-1].get("content")) if assistant else (texts[-1] if texts else "")
    return {"text": final, "messages": texts}


def upload(path):
    file = Path(path)
    content = file.read_bytes()
    body, content_type = _multipart([], [("files", file.name, content)])
    return _api("/workspace/files/upload", method="POST", data=body, headers={"Content-Type": content_type}, timeout=60)


def main(argv):
    if len(argv) < 2:
        print("用法: sp-bridge login | agents | ask <agent> <prompt> | wait <thread> | pull <thread> | upload <file>")
        return 2
    command = argv[1]
    try:
        if command == "login":
            capture_login()
            print("已保存登录，权限 0600")
        elif command == "agents":
            for row in agents():
                print("{}\t{}".format(row["agent_id"], row["name"]))
        elif command == "ask":
            if len(argv) < 4:
                print("用法: sp-bridge ask <agent> <prompt>")
                return 2
            print(json.dumps(ask(argv[2], argv[3]), ensure_ascii=False))
        elif command == "wait":
            print(wait(argv[2]))
        elif command == "pull":
            print(pull(argv[2])["text"])
        elif command == "upload":
            print(json.dumps(upload(argv[2]), ensure_ascii=False))
        else:
            print("未知命令: {}".format(command))
            return 2
    except BridgeError as error:
        print(str(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
