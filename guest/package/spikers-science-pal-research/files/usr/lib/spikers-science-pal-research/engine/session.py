"""Hand a research goal to the Omarchy agent the user already connected.

The agent decides the procedure. The nine-step calculator and the
SciencePal window are tools it may call, not a path every goal must take.
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
        "你是这台虚拟机上的科研助手。用户的目的是：\n"
        f"{goal}\n\n"
        "由你决定步骤。不要把每个目的都做成回归或材料筛选。\n"
        "你可以调用整台系统，包括终端、文件，以及下面两个入口。\n"
        "应用1，本机计算：只有当目的确实是在一张表上做特征、模型、筛选时，才运行\n"
        f"   spikers-science-pal-engine --execute --goal '{quoted}'\n"
        "   然后只引用它写出的 report.html 和 csv。写着「离线回退」的数字不能当结论。\n"
        "应用2，平台：需要平台上的 Agent、检索或工作流时，运行 spikers-science-pal-sciencepal "
        "打开 https://sciencepal.ai/ 。把目的和你已经得到的文件路径写进 ~/science 下的 "
        "platform-handoff.md，方便贴进平台。\n"
        "做不到的步骤就直说，不要编造测量、文献或数据。用中文说明你实际跑了什么、文件在哪。\n"
    )
