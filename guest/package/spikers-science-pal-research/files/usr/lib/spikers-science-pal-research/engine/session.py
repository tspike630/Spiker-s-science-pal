"""Hand a research goal to the Omarchy agent the user already connected.

Omarchy does not store one shared API key. `omarchy default agent` picks
OpenCode, Claude, Codex, or another harness. The first launch of that
harness asks for its own key or browser login. `omarchy-agent --inline`
then runs it in this window, with permission prompts skipped, so it can
call the local engine and the SciencePal launcher itself.
"""

import shutil
import subprocess


def connected_agent():
    if not shutil.which("omarchy-default-agent"):
        return ""
    result = subprocess.run(["omarchy-default-agent"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def task_prompt(goal):
    quoted = goal.replace("'", "'\"'\"'")
    return (
        "你是 Spiker 科研引擎。用户的目的是：\n"
        f"{goal}\n\n"
        "你要自己调用本机的两个应用，不要编造数字。\n"
        "1. 应用1的计算：运行\n"
        f"   spikers-science-pal-engine --execute --goal '{quoted}'\n"
        "   它会把领域、数据和报告写到 ~/science。读 workspace/report.html、"
        "top10.csv 和 audit.md，只用里面的句子。\n"
        "2. 应用2的平台：运行 spikers-science-pal-sciencepal 打开 sciencepal.ai。"
        "把目的、报告路径和数据来源写进该目录的 platform-handoff.md，方便贴进平台 Agent。\n"
        "3. 用中文收尾：识别到的领域、数据是离线回退还是外部数据、报告的绝对路径。\n"
        "离线回退的数字不能当成可以引用的结论。\n"
    )
