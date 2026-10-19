#!/usr/bin/python3 -I
"""Menu entry for the research engine. A menu click opens a terminal window."""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

ENGINE = Path(__file__).resolve().parent
LIB = ENGINE.parent
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from engine.newdomain import draft, methodology_prompt, parse_method
from engine.handoff import complete_goal


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


def ask_line(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        print()
        return ""


def ask_new_domain(goal, decision):
    config = draft(goal, decision)
    print("新领域 · {}".format(config["discipline"]))
    print("直接回车就用括号里的默认。")
    source = ask_line("数据源 [{}]：".format(config["data_source"]))
    metric = ask_line("目标指标 [{}]：".format(config["metric"]))
    features = ask_line("特征，用逗号分开 [{}]：".format("、".join(config["features"])))
    if source:
        config["data_source"] = source
    if metric:
        config["metric"] = metric
    if features:
        names = [part.strip() for part in features.replace("，", ",").split(",") if part.strip()]
        if names:
            config["features"] = names[:3]
    print()
    print("若要让 SciencePal 补方法，把下面这段贴进平台 Agent，再把返回的 JSON 贴回这一行。")
    print(methodology_prompt(config))
    pasted = ask_line("JSON 或回车跳过：")
    if pasted:
        try:
            config = parse_method(pasted, config)
            print("已写入平台返回的方法学。")
        except (ValueError, json.JSONDecodeError) as error:
            print("没有解析这份 JSON：{}。继续用上面的配置。".format(error))
    return config


def wizard():
    print("Spiker 科研引擎")
    print("输入研究目的。已有领域会做完本地计算，并在已登录时自动请平台深化。")
    print("新领域会先向平台要方法学；平台不可达时再请你补三项，或贴回 JSON。")
    goal = ask_line("> ")
    if not goal:
        print("没有目的，已退出。")
        return 1
    offline = os.environ.get("SPIKERS_SCIENCE_PAL_ENGINE_OFFLINE") == "1"
    context = complete_goal(goal, DATA, science_root(), offline, True, ask_new_domain)
    print("\n".join(context["logs"]))
    if context.get("report"):
        print("报告：{}".format(context["report"]))
    return 0


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
        context = complete_goal(goal, DATA, science_root(), offline, False, ask_new_domain)
        print("\n".join(context["logs"]))
        report = context.get("report")
        if report:
            print("报告：{}".format(report))
        return 0
    return wizard()


if __name__ == "__main__":
    sys.exit(main())
