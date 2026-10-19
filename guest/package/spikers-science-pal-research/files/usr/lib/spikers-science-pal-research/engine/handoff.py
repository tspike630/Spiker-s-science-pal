"""Ask SciencePal after the local steps, and fall back to a printed prompt."""

from pathlib import Path

from engine.bridge import (
    FIELD_AGENTS,
    METHOD_AGENT,
    BridgeError,
    ask,
    load_token,
    pull,
    upload,
    wait,
)
from engine.newdomain import draft, methodology_prompt, parse_method
from engine.pipeline import run_pipeline
from engine.router import load_judges, route

CONSTRAINT = (
    "所有数字必须引用科研虚拟机（Spiker's Science Pal）内真实运行的实验产物"
    "（report.html/CSV），不得凭空编造；引用格式：方法+数据集+数字来源。"
    "产出结构：方法学说明→流程→结果→领域解读。"
)


def reachable():
    return bool(load_token().get("access_token"))


def fetch_method(config):
    started = ask(METHOD_AGENT, methodology_prompt(config))
    wait(started["thread_id"])
    text = pull(started["thread_id"])["text"]
    if not text:
        raise BridgeError("平台没有返回方法学。")
    return parse_method(text, config)


def deepen(context):
    judge_id = context["decision"].get("id") or ""
    agent = FIELD_AGENTS.get(judge_id, METHOD_AGENT)
    report = context.get("report")
    uploaded = []
    if report:
        for name in ("report.html", "top10.csv"):
            path = Path(report).parent / name
            if path.is_file():
                try:
                    upload(path)
                    uploaded.append(path.name)
                except BridgeError:
                    uploaded.append(path.name + " 未上传")
    excerpt = ""
    if report and Path(report).is_file():
        excerpt = Path(report).read_text(encoding="utf-8")[:4000]
    prompt = "{}\n\n目的：{}\n已上传：{}\n\n报告摘录：\n{}".format(
        CONSTRAINT, context["goal"], "、".join(uploaded) or "无", excerpt)
    started = ask(agent, prompt)
    wait(started["thread_id"])
    text = pull(started["thread_id"])["text"]
    export = Path(context["export"]) if context.get("export") else Path(report).parent
    export.mkdir(parents=True, exist_ok=True)
    destination = export / "platform.md"
    destination.write_text(
        "# 平台深化\n\nAgent：{}\n\n{}\n".format(agent, text or "平台没有文本回复。"),
        encoding="utf-8")
    return destination


def complete_goal(goal, judges_path, science, offline, interactive, ask_new):
    decision = route(goal, load_judges(judges_path))
    config = None
    early = []
    if not decision["known"]:
        config = draft(goal, decision)
        if not offline and reachable():
            try:
                config = fetch_method(config)
                early.append("[平台] 方法学已取回 ✓")
            except BridgeError as error:
                early.append("[平台] 方法学不可达：{}".format(error))
                print(methodology_prompt(config))
                if interactive:
                    config = ask_new(goal, decision)
        elif interactive:
            config = ask_new(goal, decision)
        elif not offline:
            early.append("[平台] 尚未登录。打开应用2登录后运行 sp-bridge login。")
            print(methodology_prompt(config))
    context = run_pipeline(goal, judges_path, science, offline=offline, config=config)
    context["logs"][1:1] = early
    if decision["known"] and not offline and reachable():
        try:
            path = deepen(context)
            context["logs"].append("[平台] Agent 深化完成 ✓ {}".format(path.name))
        except BridgeError as error:
            context["logs"].append("[平台] 不可达，本地报告已保留：{}".format(error))
    elif decision["known"] and not offline:
        context["logs"].append("[平台] 尚未登录。打开应用2登录后运行 sp-bridge login，本次只保留本地报告。")
    return context
