"""Run the nine steps in order. A failed step is logged and the rest still run."""

import os
from pathlib import Path

from engine.newdomain import draft
from engine.router import load_judges, route
from engine.steps import STEPS, prepare_directory


def run_pipeline(goal, judges_path, science, offline=False, stamp="latest", config=None):
    judges = load_judges(judges_path)
    decision = route(goal, judges)
    if config is None and not decision["known"]:
        config = draft(goal.strip(), decision)
    context = {
        "goal": goal.strip(),
        "decision": decision,
        "science": str(science),
        "offline": offline,
        "stamp": stamp,
        "config": config or {},
    }
    prepare_directory(context)
    logs = ["识别领域：{}".format(decision["label"] if decision["known"] else decision["label"] + " · 已写骨架")]
    for step in STEPS:
        try:
            logs.append(step(context))
        except (OSError, ValueError, ZeroDivisionError, KeyError) as error:
            logs.append("[失败] {} · {}".format(step.__name__, error))
    context["logs"] = logs
    return context
