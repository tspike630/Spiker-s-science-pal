#!/usr/bin/python3 -I
"""Menu entry for the research engine. A menu click opens a terminal window."""

import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ENGINE = Path(__file__).resolve().parent
LIB = ENGINE.parent
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from engine.pipeline import run_pipeline
from engine.session import connected_agent, task_prompt


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
    print("输入一个科研目的。已连接的模型会自己调用本机的 9 步计算，并打开 SciencePal。")
    try:
        return input("> ").strip()
    except EOFError:
        print()
        return ""


def connect_model():
    print("和 OpenCode 一样：先选定模型。第一次打开时，由它自己要求 API key 或浏览器登录。")
    print("密钥留在那个模型自己的目录里，不会写进科研包。")
    if shutil.which("omarchy-menu"):
        subprocess.run(["omarchy-menu", "summon", "setup.default.agent"], check=False)
    else:
        print("在终端执行：omarchy default agent opencode")
    agent = connected_agent()
    if not agent:
        print("还没有默认模型。在刚才的菜单里选一个，例如 OpenCode，然后再回到这里。")
        return
    print("现在打开 {}。登录完成后关掉它，再选 2。".format(agent))
    if shutil.which(agent):
        subprocess.run([agent], check=False)
    else:
        print("找不到 {}。在终端运行一次这个命令，Omarchy 会在第一次使用时安装它。".format(agent))


def delegate(goal):
    agent = connected_agent()
    if not agent or not shutil.which("omarchy-agent"):
        print("没有已连接的模型，改为在本机走完 9 步。")
        return False
    print("交给 {}。它会运行科研引擎，并打开 SciencePal。".format(agent))
    os.execvp("omarchy-agent", ["omarchy-agent", "--inline", "--prompt", task_prompt(goal)])
    return True


def wizard():
    while True:
        print()
        print("  1  连接模型（API key）")
        print("  2  输入目的，让模型自己完成")
        print("  q  退出")
        try:
            choice = input("选择：").strip().lower()
        except EOFError:
            print()
            return 0
        if choice in {"q", "quit", "exit"}:
            return 0
        if choice == "1":
            connect_model()
        elif choice == "2":
            goal = ask_goal()
            if not goal:
                print("没有目的。")
                continue
            if delegate(goal):
                return 0
            offline = os.environ.get("SPIKERS_SCIENCE_PAL_ENGINE_OFFLINE") == "1"
            context = run_pipeline(goal, DATA, science_root(), offline=offline)
            print("\n".join(context["logs"]))
            if context.get("report"):
                print("报告：{}".format(context["report"]))
        elif choice:
            print("没有这一项。")


def main():
    parser = argparse.ArgumentParser(description="Run the nine-step research engine")
    parser.add_argument("--goal", default="")
    parser.add_argument("--execute", action="store_true", help="run the nine steps locally; an agent calls this")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--inside", action="store_true")
    args = parser.parse_args()
    foreground = os.environ.get("SPIKERS_SCIENCE_PAL_ENGINE_FOREGROUND")
    if not args.inside and not foreground and not args.goal and not args.execute and not sys.stdin.isatty():
        open_window()
    if args.execute or args.goal:
        goal = args.goal.strip()
        if not goal:
            print("没有目的，已退出。")
            return 1
        offline = args.offline or os.environ.get("SPIKERS_SCIENCE_PAL_ENGINE_OFFLINE") == "1"
        context = run_pipeline(goal, DATA, science_root(), offline=offline)
        print("\n".join(context["logs"]))
        report = context.get("report")
        if report:
            print("报告：{}".format(report))
        return 0
    return wizard()


if __name__ == "__main__":
    sys.exit(main())
