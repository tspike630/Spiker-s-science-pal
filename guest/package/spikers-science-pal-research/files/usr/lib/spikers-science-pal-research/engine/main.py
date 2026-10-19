#!/usr/bin/python3 -I
"""Menu entry for the research engine. A menu click opens a terminal window."""

import argparse
import os
from pathlib import Path
import shlex
import shutil
import sys

ENGINE = Path(__file__).resolve().parent
LIB = ENGINE.parent
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from engine.keys import NAMES, get, save, load
from engine.pipeline import run_pipeline


DATA = os.environ.get("SPIKERS_SCIENCE_PAL_JUDGES_DATA") or "/usr/share/spikers-science-pal-research/judges.json"


def science_root():
    home = Path(os.environ["HOME"])
    return Path(os.environ.get("SCIENCE_ROOT") or home / "science")


def open_window():
    script = str(Path(sys.argv[0]).resolve())
    python = sys.executable or "python3"
    inner = " ".join(shlex.quote(part) for part in (python, "-I", script, "--inside"))
    terminal = shutil.which("xdg-terminal-exec")
    if terminal:
        command = [terminal, "--app-id=dev.spikerssciencepal.engine", "--title=Spiker 科研引擎", "-e", "bash", "-c", inner]
        if shutil.which("uwsm-app") and shutil.which("setsid"):
            command = ["setsid", "uwsm-app", "--", *command]
        elif shutil.which("setsid"):
            command = ["setsid", *command]
        os.execvp(command[0], command)
    presentation = shutil.which("omarchy-launch-floating-terminal-with-presentation")
    if presentation:
        os.execvp(presentation, [presentation, python, "-I", script, "--inside"])


def ask_goal():
    print("Spiker 科研引擎")
    print("输入一个科研目的。引擎用同一套 9 步处理：问题、文献、数据、特征、建模、解释、筛选、核查、产出。")
    print("能对上已有领域就用该领域的数据源；对不上就先建领域骨架，再跑完这 9 步。")
    try:
        return input("> ").strip()
    except EOFError:
        print()
        return ""


def ask_keys():
    if not sys.stdin.isatty():
        return
    current = load()
    changed = False
    for name in NAMES:
        if get(name):
            continue
        try:
            value = input("{} API key（直接回车跳过）：".format(name)).strip()
        except EOFError:
            print()
            return
        if not value:
            continue
        current[name] = value
        changed = True
    if changed:
        written = save(current)
        print("已写入 {}（权限 0600）".format(written))


def main():
    parser = argparse.ArgumentParser(description="Run the nine-step research engine")
    parser.add_argument("--goal", default="")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--inside", action="store_true")
    args = parser.parse_args()
    foreground = os.environ.get("SPIKERS_SCIENCE_PAL_ENGINE_FOREGROUND")
    if not args.inside and not foreground and not args.goal and not sys.stdin.isatty():
        open_window()
    goal = args.goal.strip() or ask_goal()
    if not goal:
        print("没有目的，已退出。")
        return 1
    if sys.stdin.isatty() and not args.offline:
        ask_keys()
    offline = args.offline or os.environ.get("SPIKERS_SCIENCE_PAL_ENGINE_OFFLINE") == "1"
    context = run_pipeline(goal, DATA, science_root(), offline=offline)
    print("\n".join(context["logs"]))
    report = context.get("report")
    if report:
        print("报告：{}".format(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
