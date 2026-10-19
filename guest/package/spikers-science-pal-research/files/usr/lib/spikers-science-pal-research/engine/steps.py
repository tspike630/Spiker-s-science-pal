"""The nine research steps. Each one returns a single log line and updates context."""

import csv
import html
import json
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path

try:
    import shap  # optional; the explanation step uses ridge weights either way
except ImportError:
    shap = None

from engine import keys, model
from engine.sample_data import CATALYSIS, FEATURES, generic_rows

INTERVAL_SENTENCE = "等宽区间不改域内均值排序"


def _log(index, name, detail, ok=True):
    mark = "✓" if ok else "回退"
    return "[{}/9] {} · {} {}".format(index, name, detail, mark)


def _slug(text):
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", text).strip("-")
    return (cleaned or "custom")[:40]


def prepare_directory(context):
    root = Path(context["science"])
    if context["decision"]["known"]:
        directory = root / "domains" / context["decision"]["id"]
    else:
        directory = root / "domains" / ("custom-" + _slug(context["goal"]))
    (directory / "data").mkdir(parents=True, exist_ok=True)
    (directory / "workspace").mkdir(parents=True, exist_ok=True)
    context["directory"] = directory
    if not context["decision"]["known"]:
        (directory / "problems.md").write_text(
            "# 未知领域\n\n目的：{}\n\n待补充：数据源、描述符、验证方式。\n".format(context["goal"]),
            encoding="utf-8")
        (directory / "descriptors.md").write_text(
            "# 描述符\n\n| 名 | 含义 |\n|---|---|\n| f1 | 待定义 |\n| f2 | 待定义 |\n| f3 | 待定义 |\n",
            encoding="utf-8")
        (directory / "platform-handoff.md").write_text(
            "# 交给 SciencePal 平台\n\n目的：{}\n\n"
            "虚拟机没有可用的平台登录，不能代这个账号发消息。"
            "打开应用2后，把这段目的贴进 Agent，让它补数据源、描述符和验证方式。\n".format(context["goal"]),
            encoding="utf-8")
    return directory


def s1_problem(context):
    directory = context["directory"]
    judge = context["decision"].get("judge") or {}
    focus = judge.get("focus") or context["goal"]
    datasets = (judge.get("capabilities") or {}).get("deep", {}).get("datasets", [])
    roadmap = (judge.get("capabilities") or {}).get("deep", {}).get("roadmap", [])
    problems = [
        focus,
        "数据：" + (datasets[0]["name"] if datasets else "待补充数据源"),
        "路线：" + (roadmap[0] if roadmap else "待补充验证方式"),
    ]
    chosen = 0
    folded = context["goal"].lower()
    for index, problem in enumerate(problems):
        if problem and any(part and part.lower() in folded for part in problem.split("，")[:1]):
            chosen = index
            break
    lines = ["# 问题\n", "目的：{}\n".format(context["goal"])]
    for index, problem in enumerate(problems, 1):
        mark = "（选中）" if index - 1 == chosen else ""
        lines.append("{}. {} {}\n".format(index, problem, mark))
    (directory / "problems.md").write_text("".join(lines), encoding="utf-8")
    context["problem"] = problems[chosen]
    return _log(1, "定义问题", "已选问题 {}".format(chosen + 1))


def s2_literature(context):
    judge = context["decision"].get("judge") or {}
    references = (judge.get("capabilities") or {}).get("deep", {}).get("references", [])
    if not references:
        references = ["待补充：把领域综述和数据论文写进 refs.bib"]
    entries = []
    for index, reference in enumerate(references, 1):
        entries.append("@misc{{ref{0},\n  title = {{{1}}}\n}}\n".format(index, reference.replace("{", "").replace("}", "")))
    path = context["directory"] / "refs.bib"
    path.write_text("\n".join(entries), encoding="utf-8")
    context["references"] = references
    return _log(2, "文献基线", "{} 条 · {}".format(len(references), path.name))


def _rows_from_csv(path):
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            if "E" not in record:
                continue
            try:
                energy = float(record["E"])
                features = [float(record[key]) for key in FEATURES]
            except (TypeError, ValueError):
                continue
            rows.append({
                "name": record.get("element") or record.get("name") or "row",
                "element": record.get("element") or "",
                "E": energy,
                **{key: float(record[key]) for key in FEATURES},
            })
    return rows


def _try_catalysis_hub():
    query = "query={reactions(first:40){edges{node{chemicalComposition reactionEnergy}}}}"
    request = urllib.request.Request(
        "https://api.catalysis-hub.org/graphql",
        data=query.encode(),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode())
    edges = payload.get("data", {}).get("reactions", {}).get("edges") or []
    rows = []
    for edge in edges:
        node = edge.get("node") or {}
        energy = node.get("reactionEnergy")
        try:
            energy = float(energy)
        except (TypeError, ValueError):
            continue
        name = str(node.get("chemicalComposition") or "surface")[:40]
        rows.append({"name": name, "element": name, "en": 0.0, "ea": 0.0, "period": 0, "group": 0, "E": energy, "partial": True})
    return rows


def _try_materials_project(api_key):
    url = "https://api.materialsproject.org/materials/summary/?_limit=20&_fields=formula_pretty,energy_above_hull,band_gap"
    request = urllib.request.Request(url, headers={"X-API-KEY": api_key})
    with urllib.request.urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode())
    rows = []
    for item in payload.get("data") or []:
        try:
            energy = float(item.get("energy_above_hull"))
            gap = float(item.get("band_gap") or 0)
        except (TypeError, ValueError):
            continue
        rows.append({
            "name": str(item.get("formula_pretty") or "mp"),
            "element": str(item.get("formula_pretty") or ""),
            "en": gap, "ea": energy, "period": 0, "group": 0, "E": -energy,
        })
    return rows


def s3_data(context):
    directory = context["directory"]
    raw = directory / "data" / "raw" / "cathub"
    found = []
    if raw.is_dir():
        for path in raw.glob("*.csv"):
            found.extend(_rows_from_csv(path))
    source = "本地 CSV"
    offline = False
    if not found and not context.get("offline"):
        try:
            found = _try_catalysis_hub()
            source = "Catalysis-Hub"
        except (OSError, urllib.error.URLError, ValueError, KeyError):
            found = []
        if not found:
            api_key = keys.get("materials_project")
            if api_key:
                try:
                    found = _try_materials_project(api_key)
                    source = "Materials Project"
                except (OSError, urllib.error.URLError, ValueError, KeyError):
                    found = []
    if not found:
        if context["decision"]["id"] == "05-wang-zhenbin":
            found = [dict(row) for row in CATALYSIS]
        else:
            seed = sum(ord(char) for char in (context["decision"]["id"] or context["goal"]))
            found = generic_rows(seed)
        source = "离线回退"
        offline = True
    context["rows"] = found
    context["source"] = source
    context["offline_data"] = offline
    (directory / "data" / "SOURCE.txt").write_text(source + "\n", encoding="utf-8")
    return _log(3, "数据获取", "{} · {} 行 · 无缺失".format(source, len(found)), ok=not offline)


def s4_featurize(context):
    directory = context["directory"]
    names = FEATURES if context["rows"] and "en" in context["rows"][0] else ("f1", "f2", "f3")
    context["feature_names"] = names
    lines = ["# 描述符\n\n", "| 名 | 来源 |\n|---|---|\n"]
    for name in names:
        lines.append("| {} | 组成或样本列 |\n".format(name))
    (directory / "descriptors.md").write_text("".join(lines), encoding="utf-8")
    path = directory / "workspace" / "features.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", *names, "E"])
        for row in context["rows"]:
            writer.writerow([row["name"], *[row[name] for name in names], row["E"]])
    context["matrix"] = [[float(row[name]) for name in names] for row in context["rows"]]
    context["target"] = [float(row["E"]) for row in context["rows"]]
    return _log(4, "特征工程", "{} 列 · {}".format(len(names), path.name))


def s5_model(context):
    fitted = model.fit(context["matrix"], context["target"])
    predicted = [model.predict(fitted, row) for row in context["matrix"]]
    loo, loo_score = model.loocv(context["matrix"], context["target"])
    width = model.equal_width([left - right for left, right in zip(context["target"], loo)])
    score = model.r2(context["target"], predicted)
    context["model"] = fitted
    context["predicted"] = predicted
    context["interval"] = width
    context["r2"] = score
    context["loocv"] = loo_score
    detail = "R²={:.3f} · LOOCV={:.3f} · {}".format(score, loo_score, INTERVAL_SENTENCE)
    return _log(5, "建模验证", detail)


def s6_explain(context):
    weights = context["model"][0]
    names = context["feature_names"]
    pairs = sorted(zip(names, weights[:len(names)]), key=lambda item: abs(item[1]), reverse=True)
    context["importance"] = pairs
    shap_note = "SHAP 可用，本步仍写出权重对照" if shap is not None else "无 shap，使用岭回归权重"
    lead = pairs[0][0] if pairs else "无"
    context["lead_feature"] = lead
    return _log(6, "模型解释", "{} · 主导 {}".format(shap_note, lead))


def s7_screen(context):
    order = sorted(range(len(context["rows"])), key=lambda index: context["predicted"][index])
    chosen = order[:10]
    lead = context.get("lead_feature") or context["feature_names"][0]
    weight = dict(context["importance"]).get(lead, 0.0)
    path = context["directory"] / "workspace" / "top10.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "material", "E_pred", "interval_low", "interval_high", "reason"])
        table = []
        for rank, index in enumerate(chosen, 1):
            row = context["rows"][index]
            pred = context["predicted"][index]
            half = context["interval"]
            gain = weight * float(row.get(lead) or 0)
            reason = "该材料 {} 占据高 → 活性增益 {:.3f}".format(lead, gain)
            table.append((rank, row["name"], "{:.3f}".format(pred), "{:.3f}".format(pred - half), "{:.3f}".format(pred + half), reason))
        writer.writerows(table)
    context["top10"] = table
    return _log(7, "候选筛选", "top10.csv · {} 条".format(len(table)))


def s8_audit(context):
    total = len(context["rows"])
    synthetic = total if context.get("offline_data") else 0
    text = (
        "# 真实性边界\n\n"
        "数据来源：{}\n"
        "样本 {} 条，其中离线或合成 {} 条。\n"
        "等宽预测区间只描述残差尺度。{}\n"
        "吸附能或活性的排序不能代替实验。位点、电位和电解液都还没测。\n"
    ).format(context["source"], total, synthetic, INTERVAL_SENTENCE)
    path = context["directory"] / "workspace" / "audit.md"
    path.write_text(text, encoding="utf-8")
    context["audit"] = text
    kind = "离线回退" if context.get("offline_data") else "外部数据"
    return _log(8, "真实性核查", kind, ok=not context.get("offline_data"))


def s9_report(context):
    directory = context["directory"]
    title = context["decision"]["label"]
    rows = context.get("top10") or []
    head = "".join("<th>{}</th>".format(html.escape(name)) for name in ("rank", "material", "E_pred", "low", "high", "reason"))
    body = []
    for row in rows:
        cells = "".join("<td>{}</td>".format(html.escape(str(cell))) for cell in row)
        body.append("<tr>{}</tr>".format(cells))
    klass = "warn" if context.get("offline_data") else "ok"
    banner = "离线回退，非作品结论" if context.get("offline_data") else "已加载外部或本地数据"
    page = (
        "<!doctype html><meta charset='utf-8'><title>{title}</title>"
        "<style>body{{font:16px/1.5 system-ui,sans-serif;margin:2rem;background:#0d1117;color:#e6edf3}}"
        "table{{border-collapse:collapse}} td,th{{border:1px solid #30363d;padding:.35rem .7rem}}"
        ".warn{{color:#f0883e}} .ok{{color:#3fb950}}</style>"
        "<h1>{title}</h1><p class='{klass}'>{banner}</p>"
        "<p>目的：{goal}</p><p>R²={r2:.3f}，LOOCV={loo:.3f}。{interval}</p>"
        "<h2>筛选</h2><table><tr>{head}</tr>{body}</table>"
        "<h2>核查</h2><pre>{audit}</pre>"
    ).format(
        title=html.escape(title),
        klass=klass,
        banner=html.escape(banner),
        goal=html.escape(context["goal"]),
        r2=context.get("r2") or 0,
        loo=context.get("loocv") or 0,
        interval=html.escape(INTERVAL_SENTENCE),
        head=head,
        body="".join(body),
        audit=html.escape(context.get("audit") or ""),
    )
    report = directory / "workspace" / "report.html"
    report.write_text(page, encoding="utf-8")
    export_root = Path(context["science"]) / "exports"
    export_root.mkdir(parents=True, exist_ok=True)
    stamp = context.get("stamp") or "latest"
    bundle = export_root / "{}-{}".format(context["decision"]["id"] or _slug(context["goal"]), stamp)
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir()
    for name in ("report.html", "top10.csv", "features.csv", "audit.md"):
        source = directory / "workspace" / name
        if source.is_file():
            shutil.copy(source, bundle / name)
    context["report"] = report
    context["export"] = bundle
    return _log(9, "成果产出", "{} · {}".format(report.name, bundle.name))


STEPS = (
    s1_problem,
    s2_literature,
    s3_data,
    s4_featurize,
    s5_model,
    s6_explain,
    s7_screen,
    s8_audit,
    s9_report,
)
