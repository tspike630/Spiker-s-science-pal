"""API keys live only in the user's config file, mode 0600."""

import json
import os
from pathlib import Path

NAMES = ("materials_project", "openai")


def path():
    home = Path(os.environ["HOME"])
    config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    return config / "spikers-science-pal" / "api_keys.json"


def load():
    file = path()
    if not file.is_file():
        return {}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(data):
    file = path()
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.chmod(file, 0o600)
    return file


def get(name):
    value = load().get(name) or ""
    return str(value).strip()
